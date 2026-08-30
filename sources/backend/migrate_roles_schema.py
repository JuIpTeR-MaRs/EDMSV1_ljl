"""Database migration for roles and hierarchy schema."""
import os
import pymysql
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("DATABASE_URL", "mysql+pymysql://root:123456@127.0.0.1:3306/edms_db")
engine = create_engine(db_url)

with engine.connect() as conn:
    print("[Migration] Checking and applying database schema updates...")

    # 1. Create roles table if not exists
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS roles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(64) NOT NULL UNIQUE,
        name VARCHAR(128) NOT NULL,
        name_en VARCHAR(128) NULL,
        level INT NOT NULL DEFAULT 1,
        sort_order INT NOT NULL DEFAULT 0,
        description VARCHAR(512) NULL,
        is_system BOOLEAN NOT NULL DEFAULT 0,
        can_manage_users BOOLEAN NOT NULL DEFAULT 0,
        can_manage_depts BOOLEAN NOT NULL DEFAULT 0,
        can_view_all_docs BOOLEAN NOT NULL DEFAULT 0,
        INDEX idx_role_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """))
    conn.commit()
    print("  [OK] roles table verified.")

    # 2. Check and add columns to users table
    user_cols = conn.execute(text("SHOW COLUMNS FROM users")).fetchall()
    user_col_names = [c[0] for c in user_cols]
    if "role_id" not in user_col_names:
        conn.execute(text("ALTER TABLE users ADD COLUMN role_id INT NULL AFTER department_id;"))
        conn.commit()
        print("  [OK] Added role_id column to users table.")
    else:
        print("  [OK] users.role_id already exists.")

    # 3. Check and add columns to departments table
    dept_cols = conn.execute(text("SHOW COLUMNS FROM departments")).fetchall()
    dept_col_names = [c[0] for c in dept_cols]
    if "parent_id" not in dept_col_names:
        conn.execute(text("ALTER TABLE departments ADD COLUMN parent_id INT NULL AFTER name_en;"))
        conn.commit()
        print("  [OK] Added parent_id column to departments table.")
    if "level" not in dept_col_names:
        conn.execute(text("ALTER TABLE departments ADD COLUMN level INT NOT NULL DEFAULT 1 AFTER parent_id;"))
        conn.commit()
        print("  [OK] Added level column to departments table.")

    # 4. Bootstrap default roles in MySQL
    default_roles = [
        ("super_admin", "系统管理员", "System Admin", 100, 1, 1, 1, 1, 1, "系统最高权限管理员，拥有全局控制与管理权限"),
        ("director", "总监 / 高级主管", "Director / Senior Executive", 80, 2, 0, 1, 1, 1, "高级管理层，可跨部门监管业务与文档审批"),
        ("dept_manager", "部门经理", "Department Manager", 50, 3, 1, 1, 0, 0, "部门主管，负责本部门成员与业务文档审批"),
        ("staff", "普通员工", "Staff Member", 10, 4, 1, 0, 0, 0, "常规业务成员，可创建、协作和处理日常文档")
    ]
    for code, name, name_en, level, sort_order, is_system, can_users, can_depts, can_docs, desc in default_roles:
        existing = conn.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": code}).fetchone()
        if not existing:
            conn.execute(text("""
                INSERT INTO roles (code, name, name_en, level, sort_order, is_system, can_manage_users, can_manage_depts, can_view_all_docs, description)
                VALUES (:code, :name, :name_en, :level, :sort_order, :is_system, :can_users, :can_depts, :can_docs, :desc)
            """), {
                "code": code, "name": name, "name_en": name_en, "level": level, "sort_order": sort_order,
                "is_system": is_system, "can_users": can_users, "can_depts": can_depts, "can_docs": can_docs, "desc": desc
            })
    conn.commit()
    print("  [OK] Default roles inserted / verified.")

    # 5. Link existing users to corresponding roles
    admin_role_id = conn.execute(text("SELECT id FROM roles WHERE code = 'super_admin'")).fetchone()[0]
    manager_role_id = conn.execute(text("SELECT id FROM roles WHERE code = 'dept_manager'")).fetchone()[0]
    staff_role_id = conn.execute(text("SELECT id FROM roles WHERE code = 'staff'")).fetchone()[0]

    # Assign super admin
    conn.execute(text("UPDATE users SET role_id = :rid WHERE login_name = 'admin' OR is_super_admin = 1"), {"rid": admin_role_id})
    # Assign managers
    conn.execute(text("UPDATE users SET role_id = :rid WHERE is_manager = 1 AND (role_id IS NULL OR role_id = 0)"), {"rid": manager_role_id})
    # Assign regular staff
    conn.execute(text("UPDATE users SET role_id = :rid WHERE role_id IS NULL OR role_id = 0"), {"rid": staff_role_id})
    conn.commit()
    print("  [OK] All existing users assigned to corresponding roles.")

print("[Migration] Completed successfully!")
