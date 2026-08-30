"""Tests for multi-level roles and rank hierarchy."""
import pytest
from app.extensions import db
from app.models.core import User, Department, Role
from flask_jwt_extended import create_access_token


def test_default_roles_bootstrap(app):
    with app.app_context():
        # Query bootstrapped roles
        roles = Role.query.order_by(Role.level.desc()).all()
        codes = [r.code for r in roles]
        assert "super_admin" in codes
        assert "director" in codes
        assert "dept_manager" in codes
        assert "staff" in codes

        admin_role = Role.query.filter_by(code="super_admin").first()
        assert admin_role.level == 100
        assert admin_role.is_system is True


def test_role_crud_and_reorder_api(app, client):
    with app.app_context():
        # Setup super admin
        admin = User.query.filter_by(login_name="admin").first()
        if not admin:
            admin = User(login_name="admin", employee_no="ADMIN001", first_name="Sys", last_name="Admin", is_super_admin=True, is_manager=True)
            db.session.add(admin)
            db.session.commit()
        token = create_access_token(identity=str(admin.id))

        # 1. List roles
        resp = client.get("/api/users/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 4

        # 2. Create custom high-level role: "Vice President" (level 85)
        create_resp = client.post(
            "/api/users/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "集团副总裁",
                "name_en": "Vice President",
                "code": "vp",
                "level": 85,
                "description": "分管多部门的高级管理人员",
                "can_view_all_docs": True,
                "can_manage_users": True,
                "can_manage_depts": True
            }
        )
        assert create_resp.status_code == 201
        new_role_id = create_resp.get_json()["id"]

        # 3. Update role
        up_resp = client.patch(
            f"/api/users/roles/{new_role_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "执行副总裁",
                "level": 90
            }
        )
        assert up_resp.status_code == 200

        # Verify role updated
        vp_role = db.session.get(Role, new_role_id)
        assert vp_role.name == "执行副总裁"
        assert vp_role.level == 90

        # 4. Create user with this role
        dept = Department.query.first()
        if not dept:
            dept = Department(name="总经办", code="EXEC")
            db.session.add(dept)
            db.session.commit()

        u_resp = client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "employee_no": "VP001",
                "login_name": "vp_user",
                "first_name": "VP",
                "last_name": "Leader",
                "password": "Password123!",
                "department_id": dept.id if dept else None,
                "role_id": new_role_id
            }
        )
        assert u_resp.status_code == 201
        vp_user_id = u_resp.get_json()["user_id"]

        vp_user = db.session.get(User, vp_user_id)
        assert vp_user.role_id == new_role_id
        assert vp_user.role_title == "执行副总裁"
        assert vp_user.role_level == 90
        assert vp_user.is_manager is True

        # 5. Cannot delete role while user is assigned
        del_resp = client.delete(f"/api/users/roles/{new_role_id}", headers={"Authorization": f"Bearer {token}"})
        assert del_resp.status_code == 400

        # Reassign user
        staff_role = Role.query.filter_by(code="staff").first()
        patch_resp = client.patch(
            f"/api/users/{vp_user_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"role_id": staff_role.id}
        )
        assert patch_resp.status_code == 200

        # Now delete role
        del_resp2 = client.delete(f"/api/users/roles/{new_role_id}", headers={"Authorization": f"Bearer {token}"})
        assert del_resp2.status_code == 200
