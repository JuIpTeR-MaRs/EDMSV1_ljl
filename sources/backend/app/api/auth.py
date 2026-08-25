import random
import base64
import threading
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, jwt_required
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from app.models import User
from app.utils.auth import current_user

bp = Blueprint("auth", __name__)

# [SECURITY - VULN-06 FIX] Server-side set of already-consumed captcha tokens.
# This ensures each captcha_token can only be validated once, preventing replay
# attacks where an attacker reuses a valid token+answer to brute-force passwords.
# _used_captcha_lock provides thread safety for concurrent requests.
_used_captcha_tokens: set = set()
_used_captcha_lock = threading.Lock()
_MAX_USED_CAPTCHA_TOKENS = 10000  # Cap to prevent memory exhaustion


def generate_captcha():
    # Simple Math Captcha
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    op = random.choice(["+", "-"])
    if op == "+":
        answer = str(num1 + num2)
    else:
        if num1 < num2:
            num1, num2 = num2, num1
        answer = str(num1 - num2)
    
    challenge = f"{num1} {op} {num2} = ?"
    
    # Generate simple SVG
    width, height = 120, 38
    noise_lines = ""
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = f"hsl({random.randint(0, 360)}, 70%, 50%)"
        noise_lines += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.5" opacity="0.6" />'
        
    noise_dots = ""
    for _ in range(30):
        cx = random.randint(0, width)
        cy = random.randint(0, height)
        r = random.uniform(1.0, 2.5)
        color = f"hsl({random.randint(0, 360)}, 60%, 60%)"
        noise_dots += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.5" />'
        
    text_content = ""
    for i, char in enumerate(challenge):
        x = 12 + i * 13 + random.randint(-1, 1)
        y = 25 + random.randint(-3, 3)
        rot = random.randint(-12, 12)
        color = f"hsl({random.randint(220, 290)}, 80%, 40%)" # theme-aligned purples/blues
        font_size = random.randint(16, 20)
        text_content += f'<text x="{x}" y="{y}" font-family="monospace, Courier" font-weight="bold" font-size="{font_size}" fill="{color}" transform="rotate({rot} {x} {y})">{char}</text>'
        
    svg = f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background: #ede9fe; border-radius: 4px; user-select: none;">
        {noise_lines}
        {noise_dots}
        {text_content}
    </svg>"""
    
    encoded_svg = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{encoded_svg}", answer


@bp.get("/captcha")
def get_captcha():
    captcha_img, answer = generate_captcha()
    serializer = URLSafeTimedSerializer(current_app.config.get("SECRET_KEY", "default-secret-key"))
    captcha_token = serializer.dumps({"answer": answer})
    return jsonify({
        "captcha_img": captcha_img,
        "captcha_token": captcha_token
    })


@bp.post("/login")
def login():
    """Login with login_name, password, and captcha."""
    data = request.get_json(silent=True) or {}
    login_name = (data.get("login_name") or "").strip()
    password = data.get("password") or ""
    captcha_answer = (data.get("captcha_answer") or "").strip()
    captcha_token = data.get("captcha_token") or ""
    
    if not login_name:
        return jsonify({"error": "login_name required"}), 400
        
    # Verify captcha (bypass in testing)
    if not current_app.config.get("TESTING"):
        if not captcha_token or not captcha_answer:
            return jsonify({"error": "captcha_required"}), 400
            
        serializer = URLSafeTimedSerializer(current_app.config.get("SECRET_KEY", "default-secret-key"))
        try:
            # [SECURITY - VULN-06 FIX] Check if this captcha token has already been used.
            # This prevents replay attacks where an attacker reuses a valid token.
            with _used_captcha_lock:
                if captcha_token in _used_captcha_tokens:
                    return jsonify({"error": "captcha_invalid"}), 400

            decrypted = serializer.loads(captcha_token, max_age=300) # 5 mins
            if decrypted.get("answer") != captcha_answer:
                return jsonify({"error": "captcha_invalid"}), 400

            # Mark token as consumed so it cannot be reused
            with _used_captcha_lock:
                if len(_used_captcha_tokens) >= _MAX_USED_CAPTCHA_TOKENS:
                    # Evict oldest entries by clearing half the set when limit reached
                    items = list(_used_captcha_tokens)
                    _used_captcha_tokens.clear()
                    _used_captcha_tokens.update(items[len(items) // 2:])
                _used_captcha_tokens.add(captcha_token)

        except SignatureExpired:
            return jsonify({"error": "captcha_expired"}), 400
        except (BadSignature, Exception):
            return jsonify({"error": "captcha_invalid"}), 400
        
    user = User.query.filter_by(login_name=login_name).first()
    if not user:
        return jsonify({"error": "Invalid login"}), 401
    
    if user.registration_status != "active":
        status_map = {
            "pending_dept": "Pending department approval",
            "pending_admin": "Pending admin approval",
            "rejected": "Your registration was rejected"
        }
        return jsonify({"error": status_map.get(user.registration_status, "Account inactive")}), 403

    if not user.check_password(password):
        return jsonify({"error": "Invalid password"}), 401
        
    token = create_access_token(identity=str(user.id))

    # Record login event for activity tracking
    try:
        from app.extensions import db
        from app.models.workflow import AuditLog
        log = AuditLog(
            user_id=user.id,
            action="LOGIN",
            summary=f"User {user.login_name} logged in",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass  # Non-critical, don't block login

    return jsonify(
        {
            "access_token": token,
            "user": {
                "id": user.id,
                "login_name": user.login_name,
                "display_name": user.display_name(),
                "employee_no": user.employee_no,
                "is_manager": user.is_manager,
                "is_super_admin": user.is_super_admin,
            },
        }
    )

@bp.post("/register")
def register():
    from app.extensions import db
    data = request.get_json(silent=True) or {}
    
    required = ["login_name", "password", "first_name", "last_name", "department_id"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400

    if User.query.filter_by(login_name=data["login_name"]).first():
        return jsonify({"error": "Login name already exists"}), 409

    user = User(
        login_name=data["login_name"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        employee_no=f"REQ_{data['login_name']}", # Temp ID
        department_id=data["department_id"],
        registration_status="pending_dept"
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush() # Get user.id

    # Registration Flow Logic will be implemented in a service or handled here
    # For now, we save the user and create the flow
    try:
        from app.models.workflow import ApprovalFlow, ApprovalParticipant
        flow = ApprovalFlow(document_id=None, flow_type="registration", status="active")
        flow.rel_id = user.id # Link to user
        db.session.add(flow)
        db.session.flush()

        # Single Step: Any manager of the target department OR the System Admin can approve
        from app.models.core import Department
        target_dept_id = data["department_id"]
        
        # 1. Target Department Managers
        managers = User.query.filter_by(department_id=target_dept_id, is_manager=True).all()
        
        # 2. System Admin
        admin_user = User.query.filter_by(login_name="admin").first()
        
        # Collect all eligible approvers for the SINGLE step
        approvers = set()
        if admin_user: approvers.add(admin_user.id)
        for m in managers: approvers.add(m.id)
        
        # If no specific managers found, allow ANY manager as fallback
        if not approvers:
            any_mgr = User.query.filter_by(is_manager=True).first()
            if any_mgr: approvers.add(any_mgr.id)

        for uid in approvers:
            part = ApprovalParticipant(flow_id=flow.id, user_id=uid, step_order=1)
            db.session.add(part)
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Registration failed during flow creation: {str(e)}"}), 500

    return jsonify({"message": "Registration submitted. Waiting for approval."}), 201


@bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(
        {
            "id": user.id,
            "login_name": user.login_name,
            "display_name": user.display_name(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "employee_no": user.employee_no,
            "is_manager": user.is_manager,
            "is_super_admin": user.is_super_admin,
            "department": {
                "id": user.department.id if user.department else None,
                "name": user.department.name if user.department else "",
                "name_en": user.department.name_en if user.department else ""
            } if user.department else None,
            "position": user.position_short
        }
    )


@bp.post("/change-password")
@jwt_required()
def change_password():
    from app.extensions import db
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    
    if not old_password or not new_password:
        return jsonify({"error": "Current and new passwords are required"}), 400
        
    if not user.check_password(old_password):
        return jsonify({"error": "Invalid current password"}), 401
        
    try:
        user.set_password(new_password)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 500
    
    return jsonify({"message": "Password updated successfully"})
