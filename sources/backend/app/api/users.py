from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models import User, Department, Role
from app.utils.auth import current_user
from datetime import datetime

bp = Blueprint("users", __name__)

# ── Role & Rank Hierarchy Management Endpoints ──────────────────────────────────────────

@bp.get("/roles")
@jwt_required(optional=True)
def list_roles():
    roles = Role.query.order_by(Role.level.desc(), Role.sort_order.asc(), Role.id.asc()).all()
    res = []
    for r in roles:
        user_count = User.query.filter_by(role_id=r.id, registration_status="active").count()
        res.append({
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "name_en": r.name_en,
            "level": r.level,
            "sort_order": r.sort_order,
            "description": r.description or "",
            "is_system": r.is_system,
            "can_manage_users": r.can_manage_users,
            "can_manage_depts": r.can_manage_depts,
            "can_view_all_docs": r.can_view_all_docs,
            "user_count": user_count
        })
    return jsonify(res)


@bp.post("/roles")
@jwt_required()
def create_role():
    admin = current_user()
    if not admin or not admin.is_super_admin:
        return jsonify({"error": "Super Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Role name is required"}), 400

    code = (data.get("code") or "").strip()
    if not code:
        import time
        code = f"role_{int(time.time())}"

    if Role.query.filter_by(code=code).first():
        return jsonify({"error": "Role code already exists"}), 409

    level = int(data.get("level", 10))
    if level >= 100 and code != "super_admin":
        level = 99

    role = Role(
        code=code,
        name=name,
        name_en=data.get("name_en"),
        level=level,
        sort_order=int(data.get("sort_order", 0)),
        description=data.get("description", ""),
        is_system=False,
        can_manage_users=bool(data.get("can_manage_users", level >= 50)),
        can_manage_depts=bool(data.get("can_manage_depts", level >= 80)),
        can_view_all_docs=bool(data.get("can_view_all_docs", level >= 80))
    )
    db.session.add(role)
    db.session.commit()
    return jsonify({
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "name_en": role.name_en,
        "level": role.level,
        "description": role.description,
        "is_system": role.is_system,
        "can_manage_users": role.can_manage_users,
        "can_manage_depts": role.can_manage_depts,
        "can_view_all_docs": role.can_view_all_docs
    }), 201


@bp.patch("/roles/<int:role_id>")
@bp.put("/roles/<int:role_id>")
@jwt_required()
def update_role(role_id: int):
    admin = current_user()
    if not admin or not admin.is_super_admin:
        return jsonify({"error": "Super Admin access required"}), 403

    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        role.name = data["name"].strip()
    if "name_en" in data:
        role.name_en = data["name_en"]
    if "description" in data:
        role.description = data["description"]
    if "level" in data:
        new_level = int(data["level"])
        if role.code == "super_admin" and new_level < 100:
            return jsonify({"error": "Super Admin level cannot be reduced below 100"}), 400
        if role.code != "super_admin" and new_level >= 100:
            new_level = 99
        role.level = new_level
    if "sort_order" in data:
        role.sort_order = int(data["sort_order"])
    if "can_manage_users" in data:
        role.can_manage_users = bool(data["can_manage_users"])
    if "can_manage_depts" in data:
        role.can_manage_depts = bool(data["can_manage_depts"])
    if "can_view_all_docs" in data:
        role.can_view_all_docs = bool(data["can_view_all_docs"])

    db.session.commit()
    return jsonify({"message": "Role updated successfully"})


@bp.delete("/roles/<int:role_id>")
@jwt_required()
def delete_role(role_id: int):
    admin = current_user()
    if not admin or not admin.is_super_admin:
        return jsonify({"error": "Super Admin access required"}), 403

    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404

    if role.is_system or role.code in ("super_admin", "dept_manager", "staff"):
        return jsonify({"error": "System pre-defined roles cannot be deleted"}), 400

    assigned_users = User.query.filter_by(role_id=role.id).count()
    if assigned_users > 0:
        return jsonify({"error": f"Cannot delete role: {assigned_users} member(s) are assigned to this role. Reassign them first."}), 400

    db.session.delete(role)
    db.session.commit()
    return jsonify({"message": "Role deleted successfully"})


@bp.post("/roles/reorder")
@jwt_required()
def reorder_roles():
    admin = current_user()
    if not admin or not admin.is_super_admin:
        return jsonify({"error": "Super Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    orders = data.get("roles", [])
    for item in orders:
        rid = item.get("id")
        if not rid:
            continue
        role = db.session.get(Role, rid)
        if role:
            if "level" in item:
                lvl = int(item["level"])
                if role.code == "super_admin":
                    lvl = 100
                elif lvl >= 100:
                    lvl = 99
                role.level = lvl
            if "sort_order" in item:
                role.sort_order = int(item["sort_order"])

    db.session.commit()
    return jsonify({"message": "Roles reordered successfully"})


@bp.get("/stats")
@jwt_required()
def get_stats():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    query = User.query.filter_by(registration_status='active')
    
    if user.login_name != 'admin':
        # Non-admins can only see their own department's stats
        if user.department_id:
            query = query.filter_by(department_id=user.department_id)
        else:
            query = query.filter_by(id=user.id) # Fallback to just themselves if no dept
            
    return jsonify({
        "total_count": query.count(),
        "status": "healthy"
    })

def generate_employee_no_for_role(role_id=None, role_level=None, role_code=None, exclude_user_id=None) -> str:
    """
    根据职级/权限等级自动生成员工编号：
    - L100 / 超级管理员: ADM001, ADM002...
    - L80~99 / 部门总监/VP: DIR001, DIR002...
    - L50~79 / 部门经理/主管: MGR001, MGR002...
    - L20~49 / 骨干/资深: SEN001, SEN002...
    - L10 / 普通员工: EMP001, EMP002...
    """
    import re
    lvl = 10
    code = ""
    if role_id:
        role = db.session.get(Role, role_id)
        if role:
            lvl = role.level or 10
            code = (role.code or "").lower()
    if role_level is not None:
        try:
            lvl = int(role_level)
        except Exception:
            pass
    if role_code:
        code = str(role_code).lower()
        
    if lvl >= 100 or code == "super_admin":
        prefix = "ADM"
    elif lvl >= 80 or "director" in code:
        prefix = "DIR"
    elif lvl >= 50 or "manager" in code:
        prefix = "MGR"
    elif lvl >= 20 or "senior" in code:
        prefix = "SEN"
    else:
        prefix = "EMP"

    existing_users = User.query.filter(User.employee_no.like(f"{prefix}%")).all()
    max_num = 0
    for u in existing_users:
        if exclude_user_id and u.id == exclude_user_id:
            continue
        m = re.search(r'\d+', u.employee_no or "")
        if m:
            try:
                num = int(m.group(0))
                if num > max_num:
                    max_num = num
            except Exception:
                pass

    next_num = max_num + 1
    candidate = f"{prefix}{next_num:03d}"
    
    # 确保不与数据库中任何其他员工编号冲突
    while User.query.filter_by(employee_no=candidate).first():
        next_num += 1
        candidate = f"{prefix}{next_num:03d}"
        
    return candidate

@bp.get("/generate-employee-no")
@jwt_required()
def api_generate_employee_no():
    role_id = request.args.get("role_id", type=int)
    role_level = request.args.get("role_level", type=int)
    role_code = request.args.get("role_code", type=str)
    exclude_user_id = request.args.get("exclude_user_id", type=int)
    
    emp_no = generate_employee_no_for_role(
        role_id=role_id,
        role_level=role_level,
        role_code=role_code,
        exclude_user_id=exclude_user_id
    )
    return jsonify({"employee_no": emp_no})

@bp.post("")
@jwt_required()
def create_user():
    admin = current_user()
    if not admin or not admin.is_manager:
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    
    required = ["login_name", "password", "first_name", "last_name"]
    if admin.is_super_admin:
        required.append("department_id")

    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400

    if User.query.filter_by(login_name=data["login_name"]).first():
        return jsonify({"error": "Login name already exists"}), 409

    role_id = data.get("role_id")
    role = db.session.get(Role, role_id) if role_id else None
    if not role:
        if data.get("is_super_admin") and admin.is_super_admin:
            role = Role.query.filter_by(code="super_admin").first()
        elif data.get("is_manager"):
            role = Role.query.filter_by(code="dept_manager").first()
        else:
            role = Role.query.filter_by(code="staff").first()

    # 💡 自动生成与职级匹配的员工编号
    emp_no = data.get("employee_no")
    if not emp_no or User.query.filter_by(employee_no=emp_no).first():
        emp_no = generate_employee_no_for_role(role_id=role.id if role else None)

    is_super = bool(role and role.level >= 100) or (data.get("is_super_admin", False) and admin.is_super_admin)
    is_mgr = bool(role and (role.level >= 50 or role.can_manage_users)) or data.get("is_manager", False)

    user = User(
        employee_no=emp_no,
        login_name=data["login_name"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        patronymic=data.get("patronymic", ""),
        department_id=admin.department_id if not admin.is_super_admin else data.get("department_id"),
        role_id=role.id if role else None,
        position_short=data.get("position_short", ""),
        gender=data.get("gender", ""),
        phone=str(data.get("phone", "")).strip(),
        email=str(data.get("email", "")).strip(),
        avatar_url=str(data.get("avatar_url", "")).strip(),
        is_manager=is_mgr,
        is_super_admin=is_super,
        registration_status="active"
    )
    user.set_password(data["password"])
    
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created successfully", "user_id": user.id, "employee_no": user.employee_no}), 201

@bp.get("/me")
@jwt_required()
def get_me():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    from app.api.auth import get_user_direct_supervisor
    from app.models.core import Position
    from datetime import date
    pos_obj = Position.query.filter_by(short_name=user.position_short).first() if user.position_short else None
    age = None
    if user.birth_date:
        today = date.today()
        age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))
    return jsonify({
        "id": user.id,
        "employee_no": user.employee_no,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.display_name(),
        "patronymic": user.patronymic,
        "login_name": user.login_name,
        "phone": user.phone or "",
        "email": user.email or "",
        "avatar_url": user.avatar_url or "",
        "gender": user.gender,
        "birth_date": user.birth_date.strftime("%Y-%m-%d") if user.birth_date else None,
        "age": age,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "department_name_en": user.department.name_en if user.department else None,
        "department": {
            "id": user.department.id if user.department else None,
            "name": user.department.name if user.department else "",
            "name_en": user.department.name_en if user.department else ""
        } if user.department else None,
        "position": user.position_short,
        "position_short": user.position_short,
        "position_full_name": pos_obj.full_name if pos_obj else (user.position_short or ""),
        "position_full_name_en": pos_obj.full_name_en if pos_obj else (user.position_short or ""),
        "role_id": user.role_id,
        "role_name": user.role.name if user.role else ("系统最高决策者" if user.is_super_admin else ("部门主管" if user.is_manager else "普通员工")),
        "role_name_en": user.role.name_en if (user.role and user.role.name_en) else ("Super Administrator" if user.is_super_admin else ("Department Supervisor" if user.is_manager else "Regular User")),
        "role_level": user.role_level,
        "role_code": user.role.code if user.role else ("super_admin" if user.is_super_admin else ("dept_manager" if user.is_manager else "staff")),
        "is_manager": user.is_manager or (user.role and user.role.level >= 50),
        "is_super_admin": user.is_super_admin or (user.role and user.role.level >= 100),
        "direct_supervisor": get_user_direct_supervisor(user)
    })

@bp.get("/me/stats")
@jwt_required()
def get_me_stats():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    from app.models import Document, DocumentVersion, DocumentPermission
    from app.models.workflow import ApprovalFlow, ApprovalParticipant, ApprovalDecision
    from sqlalchemy import or_
    
    # 1. Created docs (owned by user, active, not template)
    created_count = Document.query.filter_by(
        owner_id=user.id, 
        is_template=False, 
        deleted_at=None
    ).count()
    
    # 2. Collaborated docs (not owned by user, but user has explicit permission OR has created a version)
    collab_doc_ids = set()
    
    # a. User has permission
    perms = db.session.query(DocumentPermission.document_id)\
        .filter(DocumentPermission.user_id == user.id).all()
    for p in perms:
        collab_doc_ids.add(p[0])
        
    # b. User has edited/created a version
    versions = db.session.query(DocumentVersion.document_id)\
        .filter(DocumentVersion.created_by_id == user.id).all()
    for v in versions:
        collab_doc_ids.add(v[0])
        
    # Filter valid collaborated documents
    if collab_doc_ids:
        collaborated_count = Document.query.filter(
            Document.id.in_(list(collab_doc_ids)),
            Document.owner_id != user.id,
            Document.deleted_at == None,
            Document.is_template == False
        ).count()
    else:
        collaborated_count = 0
        
    # 3. Approved docs (owned by user that are approved OR approved by this user as reviewer/approver)
    # Documents approved by this user
    reviewed_doc_ids = db.session.query(ApprovalFlow.document_id)\
        .join(ApprovalParticipant, ApprovalParticipant.flow_id == ApprovalFlow.id)\
        .join(ApprovalDecision, ApprovalDecision.participant_id == ApprovalParticipant.id)\
        .filter(ApprovalParticipant.user_id == user.id)\
        .filter(ApprovalDecision.decision == 'approve')\
        .filter(ApprovalFlow.document_id != None)\
        .distinct().all()
        
    approved_doc_ids = [r[0] for r in reviewed_doc_ids]
    
    approved_count = Document.query.filter(
        Document.deleted_at == None,
        Document.is_template == False,
        Document.status == 'approved',
        or_(
            Document.owner_id == user.id,
            Document.id.in_(approved_doc_ids) if approved_doc_ids else False
        )
    ).count()
    
    return jsonify({
        "created_docs": created_count,
        "collaborated_docs": collaborated_count,
        "approved_docs": approved_count
    })


@bp.get("")
@jwt_required()
def list_users():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    query = User.query.filter_by(registration_status='active')
    
    # 逻辑分歧：如果是管理模式 (management=1)，且没有跨部门权限，经理只能看本部门
    is_management = request.args.get("management") == "1"
    is_super = user.is_super_admin
    has_cross_dept = bool(user.role and user.role.can_view_all_docs)
    
    if is_management and not is_super and not has_cross_dept and user.is_manager:
        query = query.filter_by(department_id=user.department_id)
    else:
        # 否则允许根据部门 ID 过滤，如果不传则默认查看全部（支持跨部门审批）
        dept_id = request.args.get("department_id")
        if dept_id:
            query = query.filter_by(department_id=dept_id)

    role_id = request.args.get("role_id")
    if role_id is not None and role_id != "":
        query = query.filter_by(role_id=int(role_id))

    is_mgr = request.args.get("is_manager")
    if is_mgr is not None and is_mgr != "":
        query = query.filter_by(is_manager=bool(int(is_mgr)))

    is_super_adm = request.args.get("is_super_admin")
    if is_super_adm is not None and is_super_adm != "":
        query = query.filter_by(is_super_admin=bool(int(is_super_adm)))

    search = request.args.get("search")

    if search:
        s = f"%{search.strip().lower()}%"
        from sqlalchemy import func
        query = query.filter(
            (func.lower(User.first_name).like(s)) | 
            (func.lower(User.last_name).like(s)) |
            (func.lower(User.login_name).like(s)) |
            (func.lower(User.employee_no).like(s)) |
            (func.lower(User.phone).like(s)) |
            (func.lower(User.email).like(s)) |
            (func.lower(User.position_short).like(s)) |
            (func.concat(func.lower(User.last_name), func.lower(User.first_name)).like(s)) |
            (func.concat(func.lower(User.last_name), " ", func.lower(User.first_name)).like(s))
        )

    sort_by = (request.args.get("sort_by") or "level").strip().lower()
    order = (request.args.get("order") or ("desc" if sort_by in ("level", "id", "created_at") else "asc")).strip().lower()

    query = query.outerjoin(Role, User.role_id == Role.id).outerjoin(Department, User.department_id == Department.id)

    from sqlalchemy import func, case
    if sort_by == "level":
        level_expr = case(
            (User.is_super_admin == True, 100),
            (Role.level.isnot(None), Role.level),
            (User.is_manager == True, 50),
            else_=10
        )
        if order == "asc":
            query = query.order_by(level_expr.asc(), User.employee_no.asc(), User.id.asc())
        else:
            query = query.order_by(level_expr.desc(), User.employee_no.asc(), User.id.asc())
    elif sort_by in ("employee_no", "emp_no", "emp"):
        if order == "desc":
            query = query.order_by(User.employee_no.desc(), User.id.desc())
        else:
            query = query.order_by(User.employee_no.asc(), User.id.asc())
    elif sort_by in ("name", "display_name"):
        if order == "desc":
            query = query.order_by(User.last_name.desc(), User.first_name.desc(), User.id.desc())
        else:
            query = query.order_by(User.last_name.asc(), User.first_name.asc(), User.id.asc())
    elif sort_by in ("department", "dept"):
        dept_name_expr = func.coalesce(Department.name, "")
        if order == "desc":
            query = query.order_by(dept_name_expr.desc(), User.id.asc())
        else:
            query = query.order_by(dept_name_expr.asc(), User.id.asc())
    elif sort_by in ("id", "created_at"):
        if order == "asc":
            query = query.order_by(User.id.asc())
        else:
            query = query.order_by(User.id.desc())
    else:
        query = query.order_by(User.id.asc())
    
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 20))
    total = query.count()
    users = query.offset((page - 1) * size).limit(size).all()
    
    items = []
    for u in users:
        items.append({
            "id": u.id,
            "employee_no": u.employee_no,
            "login_name": u.login_name,
            "display_name": u.display_name(),
            "phone": u.phone or "",
            "email": u.email or "",
            "avatar_url": u.avatar_url or "",
            "gender": u.gender or "",
            "birth_date": u.birth_date.strftime("%Y-%m-%d") if u.birth_date else None,
            "position_short": u.position_short or "",
            "department_id": u.department_id,
            "department_name": u.department.name if u.department else None,
            "department_name_en": u.department.name_en if u.department else None,
            "role_id": u.role_id,
            "role_name": u.role.name if u.role else u.role_title,
            "role_name_en": u.role.name_en if u.role else None,
            "role_level": u.role_level,
            "role_code": u.role.code if u.role else ("super_admin" if u.is_super_admin else ("dept_manager" if u.is_manager else "staff")),
            "is_manager": u.is_manager or (u.role and u.role.level >= 50),
            "is_super_admin": u.is_super_admin or (u.role and u.role.level >= 100)
        })
    return jsonify({"total": total, "items": items})

@bp.get("/<int:user_id>")
@jwt_required()
def get_user_detail(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    from app.api.auth import get_user_direct_supervisor
    from app.models.core import Position
    from datetime import date
    pos_obj = Position.query.filter_by(short_name=user.position_short).first() if user.position_short else None
    age = None
    if user.birth_date:
        today = date.today()
        age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))
    return jsonify({
        "id": user.id,
        "employee_no": user.employee_no,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.display_name(),
        "patronymic": user.patronymic,
        "login_name": user.login_name,
        "phone": user.phone or "",
        "email": user.email or "",
        "avatar_url": user.avatar_url or "",
        "gender": user.gender,
        "birth_date": user.birth_date.strftime("%Y-%m-%d") if user.birth_date else None,
        "age": age,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "department_name_en": user.department.name_en if user.department else None,
        "department": {
            "id": user.department.id if user.department else None,
            "name": user.department.name if user.department else "",
            "name_en": user.department.name_en if user.department else ""
        } if user.department else None,
        "position": user.position_short,
        "position_short": user.position_short,
        "position_full_name": pos_obj.full_name if pos_obj else (user.position_short or ""),
        "position_full_name_en": pos_obj.full_name_en if pos_obj else (user.position_short or ""),
        "role_id": user.role_id,
        "role_name": user.role.name if user.role else ("系统最高决策者" if user.is_super_admin else ("部门主管" if user.is_manager else "普通员工")),
        "role_name_en": user.role.name_en if (user.role and user.role.name_en) else ("Super Administrator" if user.is_super_admin else ("Department Supervisor" if user.is_manager else "Regular User")),
        "role_level": user.role_level,
        "role_code": user.role.code if user.role else ("super_admin" if user.is_super_admin else ("dept_manager" if user.is_manager else "staff")),
        "is_manager": user.is_manager or (user.role and user.role.level >= 50),
        "is_super_admin": user.is_super_admin or (user.role and user.role.level >= 100),
        "registration_status": user.registration_status,
        "direct_supervisor": get_user_direct_supervisor(user)
    })

@bp.patch("/<int:user_id>")
@jwt_required()
def update_user(user_id: int):
    c_user = current_user()
    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json() or {}
    
    is_super = bool(c_user and (c_user.is_super_admin or (c_user.role and c_user.role.level >= 100)))
    is_admin = bool(c_user and (c_user.is_manager or is_super or (c_user.role and (c_user.role.can_manage_users or c_user.role.can_manage_depts or c_user.role.level >= 50))))
    is_self = bool(c_user and c_user.id == target_user.id)
    
    # 💡 校验范围：普通经理仅能编辑自己部门的人员（具有用户/部门管理权限或调动部门时放行）
    if not is_super and is_admin and not (c_user.role and (c_user.role.can_view_all_docs or c_user.role.can_manage_users or c_user.role.can_manage_depts)):
        if "department_id" not in data and target_user.department_id != c_user.department_id:
            return jsonify({"error": "Forbidden: User belongs to another department"}), 403

    if not is_admin and not is_self:
        return jsonify({"error": "Forbidden"}), 403
    
    # 计算操作者与目标人员的职级权重
    c_user_level = 100 if (c_user.is_super_admin or (c_user.role and c_user.role.level >= 100)) else (c_user.role.level if c_user.role else (50 if c_user.is_manager else 10))
    target_user_level = 100 if (target_user.is_super_admin or (target_user.role and target_user.role.level >= 100)) else (target_user.role.level if target_user.role else (50 if target_user.is_manager else 10))

    # 🔒 安全规则 1：任何成员（包括系统管理员在内）无法更改自己的角色、职级或管理权限
    is_modifying_privileges = any(k in data for k in ["role_id", "is_manager", "is_super_admin"])
    if is_self and is_modifying_privileges:
        return jsonify({"error": "Forbidden: You cannot modify your own role, permissions, or administrative rank (禁止修改自己的角色或管理权限)"}), 403

    # 🔒 安全规则 2：无法更改职级高于或等于自己的同级/上级人员的权限
    if not is_self and is_modifying_privileges:
        if c_user_level <= target_user_level:
            return jsonify({"error": "Forbidden: You cannot modify the role or permissions of users with equal or higher rank (禁止修改同级或上级人员的角色权限)"}), 403

    # Fields anyone (self or admin) can change
    if "first_name" in data: target_user.first_name = data["first_name"]
    if "last_name" in data: target_user.last_name = data["last_name"]
    if "patronymic" in data: target_user.patronymic = data["patronymic"]
    if "gender" in data: target_user.gender = data["gender"]
    if "phone" in data: target_user.phone = str(data["phone"] or "").strip()
    if "email" in data: target_user.email = str(data["email"] or "").strip()
    if "avatar_url" in data: target_user.avatar_url = str(data["avatar_url"] or "").strip()
    if "position_short" in data: target_user.position_short = str(data["position_short"] or "").strip()
    if "birth_date" in data:
        bd_str = data["birth_date"]
        target_user.birth_date = datetime.strptime(bd_str, "%Y-%m-%d").date() if bd_str else None

    # Department modification: allowed for admins, or when target user has no department, or for self if manager/admin
    can_change_dept = is_admin or is_super or target_user.department_id is None or (is_self and (c_user.is_manager or c_user.is_super_admin or (c_user.role and c_user.role.level >= 50)))
    if can_change_dept and "department_id" in data:
        dept_id = data["department_id"]
        if dept_id:
            target_user.department_id = int(dept_id)
            target_user.department = db.session.get(Department, int(dept_id))
        else:
            target_user.department_id = None
            target_user.department = None
        
    # Fields ONLY admin can change
    if is_admin:
        
        if is_modifying_privileges:
            if "role_id" in data:
                r_id = data["role_id"]
                r_obj = db.session.get(Role, r_id) if r_id else None
                if r_obj:
                    if r_obj.level >= c_user_level and not (is_super and r_obj.level <= 100):
                        return jsonify({"error": "Forbidden: Cannot assign a role with rank equal to or higher than your own (禁止赋予高于或等于自身的职级)"}), 403
                    target_user.role_id = r_obj.id
                    target_user.is_super_admin = (r_obj.level >= 100)
                    target_user.is_manager = (r_obj.level >= 50 or r_obj.can_manage_users)
                else:
                    target_user.role_id = None
            elif "is_manager" in data:
                target_user.is_manager = bool(data["is_manager"])
            elif "is_super_admin" in data and is_super:
                target_user.is_super_admin = bool(data["is_super_admin"])

        if "position_short" in data: target_user.position_short = data["position_short"]
        if "employee_no" in data and data["employee_no"]:
            emp_no = str(data["employee_no"]).strip()
            existing_emp = User.query.filter_by(employee_no=emp_no).first()
            if existing_emp and existing_emp.id != target_user.id:
                return jsonify({"error": "Employee number already exists"}), 409
            target_user.employee_no = emp_no

        if "login_name" in data:
            new_login = data["login_name"].strip()
            if not new_login:
                return jsonify({"error": "Login name cannot be empty"}), 400
            existing = User.query.filter_by(login_name=new_login).first()
            if existing and existing.id != target_user.id:
                return jsonify({"error": "Login name already exists"}), 409
            target_user.login_name = new_login

        if "password" in data and data["password"] and str(data["password"]).strip():
            target_user.set_password(str(data["password"]).strip())

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 500
    return jsonify({"message": "Updated successfully"})

@bp.delete("/<int:user_id>")
@jwt_required()
def delete_user(user_id: int):
    admin = current_user()
    if not admin or not (admin.is_manager or admin.is_super_admin or (admin.role and admin.role.can_manage_users)):
        return jsonify({"error": "Admin access required"}), 403
    
    if admin.id == user_id:
        return jsonify({"error": "Cannot delete yourself (禁止删除自己)"}), 400
        
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    admin_level = 100 if (admin.is_super_admin or (admin.role and admin.role.level >= 100)) else (admin.role.level if admin.role else (50 if admin.is_manager else 10))
    user_level = 100 if (user.is_super_admin or (user.role and user.role.level >= 100)) else (user.role.level if user.role else (50 if user.is_manager else 10))
    
    # 🔒 禁止删除同级或上级人员
    if admin_level <= user_level:
        return jsonify({"error": "Forbidden: Cannot delete users with equal or higher rank (禁止删除同级或上级人员)"}), 403
    
    # 💡 范围校验：仅超级管理员可以删除所有人，经理仅能删除本部门人员
    if not admin.is_super_admin and not (admin.role and admin.role.can_view_all_docs) and user.department_id != admin.department_id:
        return jsonify({"error": "Forbidden: User is in another department"}), 403
    
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"})
    except Exception:
        db.session.rollback()
        # Fallback to safe deactivation and department removal if references exist
        u = db.session.get(User, user_id)
        if u:
            u.registration_status = "inactive"
            u.department_id = None
            u.department = None
            db.session.commit()
            return jsonify({"message": "User deactivated and removed successfully"})
        return jsonify({"error": "Failed to remove user"}), 500

@bp.post("/batch-delete")
@jwt_required()
def batch_delete_users():
    admin = current_user()
    if not admin or not (admin.is_manager or admin.is_super_admin or (admin.role and admin.role.can_manage_users)):
        return jsonify({"error": "Admin access required"}), 403
    
    data = request.get_json() or {}
    user_ids = data.get("user_ids", [])
    if not user_ids:
        return jsonify({"error": "No user IDs provided"}), 400
    
    # Filter out current admin to prevent self-deletion
    user_ids = [uid for uid in user_ids if uid != admin.id]
    
    deleted_count = 0
    errors = []
    
    for uid in user_ids:
        u = db.session.get(User, uid)
        if u:
            if not admin.is_super_admin and not (admin.role and admin.role.can_view_all_docs) and u.department_id != admin.department_id:
                errors.append(f"User ID {uid} belongs to another department - skipped")
                continue
            
            try:
                with db.session.begin_nested():
                    db.session.delete(u)
                    db.session.flush()
                deleted_count += 1
            except Exception:
                try:
                    u.registration_status = "inactive"
                    u.department_id = None
                    u.department = None
                    db.session.flush()
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"User ID {uid} could not be deleted ({str(e)})")
    
    db.session.commit()
    return jsonify({"message": f"Deleted {deleted_count} users", "errors": errors})

def is_dept_in_user_scope(user, dept_id: int) -> bool:
    """
    检查部门是否在当前用户的管理管辖范围之内：
    - 超级管理员（L100）：拥有全公司所有部门的管辖权；
    - 部门经理/主管（L50+ / is_manager）：管辖本部门及本部门的所有下属子团队（递归子树）。
    """
    if not user:
        return False
    if user.is_super_admin or (user.role and user.role.level >= 100):
        return True
    if not user.is_manager or not user.department_id:
        return False
    
    if user.department_id == dept_id:
        return True
        
    curr = db.session.get(Department, dept_id)
    visited = set()
    while curr and curr.id not in visited:
        visited.add(curr.id)
        if curr.parent_id == user.department_id:
            return True
        if not curr.parent_id:
            break
        curr = db.session.get(Department, curr.parent_id)
        
    return False

def get_user_manageable_dept_ids(user) -> list[int]:
    """获取当前用户拥有管理权限的所有部门ID列表"""
    if not user:
        return []
    if user.is_super_admin or (user.role and user.role.level >= 100):
        return [d.id for d in Department.query.all()]
    if not user.is_manager or not user.department_id:
        return []
        
    all_depts = Department.query.all()
    parent_map = {}
    for d in all_depts:
        if d.parent_id:
            parent_map.setdefault(d.parent_id, []).append(d.id)
            
    scope = [user.department_id]
    queue = [user.department_id]
    while queue:
        pid = queue.pop(0)
        children = parent_map.get(pid, [])
        for cid in children:
            if cid not in scope:
                scope.append(cid)
                queue.append(cid)
    return scope

@bp.get("/departments")
@jwt_required(optional=True)
def list_depts():
    depts = Department.query.order_by(Department.level.desc(), Department.id.asc()).all()
    return jsonify([{
        "id": d.id,
        "name": d.name,
        "name_en": d.name_en,
        "code": d.code,
        "parent_id": d.parent_id,
        "parent_name": d.parent.name if d.parent else None,
        "level": d.level if d.level is not None else 50
    } for d in depts])

@bp.post("/departments")
@jwt_required()
def create_department():
    admin = current_user()
    if not admin or not (admin.is_manager or admin.is_super_admin):
        return jsonify({"error": "Manager or Admin access required"}), 403
    
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    name_en = data.get("name_en")
    parent_id = data.get("parent_id")
    if not name:
        return jsonify({"error": "Department name is required"}), 400
    
    if Department.query.filter_by(name=name).first():
        return jsonify({"error": "Department already exists"}), 409
    
    # 权限范围检查：非超管只能在自己管辖的主部门或子团队下创建子部门
    if not admin.is_super_admin:
        if not parent_id:
            parent_id = admin.department_id
        if not is_dept_in_user_scope(admin, parent_id):
            return jsonify({"error": "Forbidden: You can only create sub-departments under your own managed department"}), 403

    level = data.get("level")
    if level is None:
        if parent_id:
            parent = db.session.get(Department, parent_id)
            if parent:
                level = max(10, (parent.level or 50) - 10)
            else:
                level = 50
        else:
            level = 50
    else:
        level = int(level)
        if not admin.is_super_admin:
            my_level = admin.role.level if admin.role else (50 if admin.is_manager else 10)
            if level > my_level:
                level = my_level

    dept = Department(
        name=name,
        name_en=name_en,
        code=f"DEPT_{name}",
        parent_id=parent_id if parent_id else None,
        level=level
    )
    db.session.add(dept)
    db.session.commit()
    return jsonify({
        "id": dept.id,
        "name": dept.name,
        "name_en": dept.name_en,
        "parent_id": dept.parent_id,
        "level": dept.level
    }), 201

@bp.delete("/departments/<int:dept_id>")
@jwt_required()
def delete_department(dept_id: int):
    admin = current_user()
    if not admin or not (admin.is_manager or admin.is_super_admin):
        return jsonify({"error": "Manager or Admin access required"}), 403
        
    dept = db.session.get(Department, dept_id)
    if not dept:
        return jsonify({"error": "Department not found"}), 404
        
    if not is_dept_in_user_scope(admin, dept.id):
        return jsonify({"error": "Forbidden: You do not have permission to delete this department"}), 403
        
    # 主管不能删除自身所在的主部门
    if not admin.is_super_admin and dept.id == admin.department_id:
        return jsonify({"error": "Forbidden: You cannot delete your own primary department"}), 403

    users_count = User.query.filter_by(department_id=dept.id).count()
    if users_count > 0:
        return jsonify({"error": "Cannot delete department because it still has members."}), 400
        
    children_count = Department.query.filter_by(parent_id=dept.id).count()
    if children_count > 0:
        return jsonify({"error": "Cannot delete department because it still has child teams."}), 400

    db.session.delete(dept)
    db.session.commit()
    return jsonify({"message": "Department deleted successfully"})


@bp.patch("/departments/<int:dept_id>")
@bp.put("/departments/<int:dept_id>")
@jwt_required()
def update_department(dept_id: int):
    admin = current_user()
    if not admin or not (admin.is_manager or admin.is_super_admin):
        return jsonify({"error": "Manager or Admin access required"}), 403
        
    dept = db.session.get(Department, dept_id)
    if not dept:
        return jsonify({"error": "Department not found"}), 404
        
    if not is_dept_in_user_scope(admin, dept.id):
        return jsonify({"error": "Forbidden: You do not have permission to manage this department"}), 403
        
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        new_name = data["name"].strip()
        existing = Department.query.filter_by(name=new_name).first()
        if existing and existing.id != dept.id:
            return jsonify({"error": "Department name already exists"}), 409
        dept.name = new_name
    if "name_en" in data:
        dept.name_en = data["name_en"]
    if "parent_id" in data:
        pid = data["parent_id"]
        if pid == dept.id:
            return jsonify({"error": "Department cannot be parent of itself"}), 400
        if pid and not is_dept_in_user_scope(admin, pid):
            return jsonify({"error": "Forbidden: Cannot move department outside of your management scope"}), 403
        dept.parent_id = pid if pid else None
        if "level" in data:
            dept.level = int(data["level"])
        elif pid:
            parent = db.session.get(Department, pid)
            if parent:
                dept.level = max(10, (parent.level or 50) - 10)
            else:
                dept.level = 50
        else:
            dept.level = 50
    elif "level" in data:
        new_lvl = int(data["level"])
        if not admin.is_super_admin:
            my_level = admin.role.level if admin.role else (50 if admin.is_manager else 10)
            if new_lvl > my_level:
                new_lvl = my_level
        dept.level = new_lvl

    db.session.commit()
    return jsonify({
        "id": dept.id,
        "name": dept.name,
        "name_en": dept.name_en,
        "parent_id": dept.parent_id,
        "level": dept.level
    })


@bp.post("/<int:user_id>/reset-password")
@jwt_required()
def reset_password(user_id: int):
    admin = current_user()
    if not admin or not (admin.is_manager or admin.is_super_admin):
        return jsonify({"error": "Admin access required"}), 403
        
    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
        
    # 💡 范围校验：部门经理仅能重置本部门人员密码
    if not admin.is_super_admin and target_user.department_id != admin.department_id:
        return jsonify({"error": "Forbidden: User belongs to another department"}), 403
        
    data = request.get_json(silent=True) or {}
    new_password = data.get("password")
    if not new_password:
        return jsonify({"error": "New password is required"}), 400
        
    try:
        target_user.set_password(new_password)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Reset failed: {str(e)}"}), 500
        
    return jsonify({"message": "Password reset successfully"})

@bp.get("/org")
@jwt_required()
def get_org():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Manager
    manager = None
    if user.manager_employee_no:
        manager_user = User.query.filter_by(employee_no=user.manager_employee_no).first()
        if manager_user:
            manager = {
                "id": manager_user.id,
                "display_name": manager_user.display_name(),
                "position": manager_user.position_short,
                "login_name": manager_user.login_name,
                "is_manager": manager_user.is_manager
            }
            
    # Peers (same department, excluding self)
    peers = []
    if user.department_id:
        peer_users = User.query.filter(
            User.department_id == user.department_id,
            User.id != user.id,
            User.registration_status == 'active'
        ).limit(15).all()
        for p in peer_users:
            peers.append({
                "id": p.id,
                "display_name": p.display_name(),
                "position": p.position_short,
                "login_name": p.login_name,
                "is_manager": p.is_manager
            })
            
    return jsonify({
        "manager": manager,
        "peers": peers,
        "department": user.department.name if user.department else "未分配部门"
    })


# ── Avatar Upload & Customization Endpoints ──────────────────────────────────────────

def _handle_avatar_upload(target_user: User):
    import os, uuid
    from flask import current_app
    
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"]:
        return jsonify({"error": "Invalid file format. Only JPG, PNG, WebP, GIF, SVG allowed."}), 400
    
    storage_base = os.environ.get("STORAGE_PATH", current_app.root_path)
    save_dir = os.path.join(storage_base, "static", "avatars")
    os.makedirs(save_dir, exist_ok=True)
    
    filename = f"avatar_{target_user.id}_{uuid.uuid4().hex[:12]}{ext}"
    save_path = os.path.join(save_dir, filename)
    file.save(save_path)
    
    avatar_url = f"/static/avatars/{filename}"
    target_user.avatar_url = avatar_url
    db.session.commit()
    
    return jsonify({
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url
    })

@bp.post("/avatar")
@jwt_required()
def upload_my_avatar():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return _handle_avatar_upload(user)

@bp.post("/<int:user_id>/avatar")
@jwt_required()
def upload_user_avatar(user_id: int):
    c_user = current_user()
    if not c_user:
        return jsonify({"error": "Unauthorized"}), 401
    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
    
    is_super = bool(c_user.is_super_admin or (c_user.role and c_user.role.level >= 100))
    is_admin = bool(c_user.is_manager or is_super or (c_user.role and (c_user.role.can_manage_users or c_user.role.can_manage_depts or c_user.role.level >= 50)))
    
    if c_user.id != target_user.id and not is_admin:
        return jsonify({"error": "Forbidden"}), 403
        
    return _handle_avatar_upload(target_user)

