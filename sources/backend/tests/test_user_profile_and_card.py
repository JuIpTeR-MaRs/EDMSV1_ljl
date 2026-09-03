import pytest
import io
from app import create_app, db
from app.config import Config
from app.models.core import User, Department, Role

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_SECRET_KEY = "test-secret-key-12345"

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_phone_email_and_detail_endpoint(app, client):
    with app.app_context():
        # Roles and default admin are already created by Bootstrap
        role_staff = Role.query.filter_by(code="staff").first()
        dept = Department(code="dept_exec", name="统筹管理部", name_en="Executive Dept", level=100)
        db.session.add(dept)
        db.session.flush()

        admin = User.query.filter_by(login_name="admin").first()
        if not admin:
            admin = User(
                login_name="admin",
                employee_no="ADM001",
                first_name="华",
                last_name="张",
                is_super_admin=True,
                is_manager=True
            )
            admin.set_password("Admin123!")
            db.session.add(admin)
        else:
            admin.set_password("Admin123!")

        admin.phone = "13800138000"
        admin.email = "admin@company.com"
        admin.avatar_url = ""
        admin.department_id = dept.id
        admin.employee_no = "ADM001"

        # Create Staff
        staff = User(
            login_name="feng_hao",
            employee_no="EMP008",
            first_name="浩",
            last_name="冯",
            phone="13912345678",
            email="fenghao@company.com",
            avatar_url="",
            department_id=dept.id,
            role_id=role_staff.id if role_staff else None,
            manager_employee_no="ADM001"
        )
        staff.set_password("123456")

        db.session.add(staff)
        db.session.commit()

        staff_id = staff.id

    # 1. Test Login to get JWT
    res = client.post("/api/auth/login", json={"login_name": "admin", "password": "Admin123!"})
    assert res.status_code == 200
    token = res.get_json().get("access_token") or res.get_json().get("token")
    assert token is not None
    assert res.get_json()["user"]["phone"] == "13800138000"
    assert res.get_json()["user"]["email"] == "admin@company.com"
    assert "avatar_url" in res.get_json()["user"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test GET /api/auth/me
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["phone"] == "13800138000"
    assert data["email"] == "admin@company.com"
    assert "avatar_url" in data

    # 3. Test GET /api/users/<staff_id> (Member Profile Card API)
    res = client.get(f"/api/users/{staff_id}", headers=headers)
    assert res.status_code == 200
    card_data = res.get_json()
    assert card_data["phone"] == "13912345678"
    assert card_data["email"] == "fenghao@company.com"
    assert card_data["department_name"] == "统筹管理部"
    assert card_data["direct_supervisor"]["employee_no"] == "ADM001"

    # 4. Test PATCH /api/users/<staff_id> (Update phone & email & preset avatar)
    res = client.patch(
        f"/api/users/{staff_id}",
        json={
            "phone": "13799998888",
            "email": "fenghao_new@company.com",
            "avatar_url": "data:image/svg+xml;utf8,<svg>preset</svg>"
        },
        headers=headers
    )
    assert res.status_code == 200

    # 5. Verify updated card data
    res = client.get(f"/api/users/{staff_id}", headers=headers)
    assert res.status_code == 200
    updated_card = res.get_json()
    assert updated_card["phone"] == "13799998888"
    assert updated_card["email"] == "fenghao_new@company.com"
    assert updated_card["avatar_url"] == "data:image/svg+xml;utf8,<svg>preset</svg>"

    # 6. Test Avatar File Upload via POST /api/users/avatar
    fake_image = (io.BytesIO(b"fake png image content"), "avatar.png")
    upload_res = client.post(
        "/api/users/avatar",
        data={"file": fake_image},
        content_type="multipart/form-data",
        headers=headers
    )
    assert upload_res.status_code == 200
    uploaded_avatar_url = upload_res.get_json()["avatar_url"]
    assert uploaded_avatar_url.startswith("/static/avatars/avatar_")

    # 7. Verify admin user's avatar_url is updated in /api/auth/me
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["avatar_url"] == uploaded_avatar_url

    # 8. Test Reset Avatar back to empty
    reset_res = client.patch(
        f"/api/users/{data['id']}",
        json={"avatar_url": ""},
        headers=headers
    )
    assert reset_res.status_code == 200
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["avatar_url"] == ""

    # 9. Test Self-Updating Department and Position
    new_dept_res = client.post(
        "/api/users/departments",
        json={"name": "技术研发部", "name_en": "R&D Department"},
        headers=headers
    )
    assert new_dept_res.status_code in (200, 201)
    new_dept_id = new_dept_res.get_json()["id"]

    dept_patch_res = client.patch(
        f"/api/users/{data['id']}",
        json={"department_id": new_dept_id, "position_short": "技术总监"},
        headers=headers
    )
    assert dept_patch_res.status_code == 200

    # Verify /api/auth/me reflects the new department and position
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    me_updated = res.get_json()
    assert me_updated["department_id"] == new_dept_id
    assert me_updated["department_name"] == "技术研发部"
    assert me_updated["position_short"] == "技术总监"
