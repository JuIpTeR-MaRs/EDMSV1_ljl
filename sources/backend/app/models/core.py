from datetime import date
from typing import TYPE_CHECKING

from app.extensions import db, BaseModel

if TYPE_CHECKING:
    from app.models.document import Document


class Role(BaseModel):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    name_en = db.Column(db.String(128), nullable=True)
    level = db.Column(db.Integer, default=1, nullable=False)  # Rank/level weight: e.g. 100=admin, 80=director, 50=manager, 10=staff
    sort_order = db.Column(db.Integer, default=0)
    description = db.Column(db.String(512), nullable=True)
    is_system = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_manage_depts = db.Column(db.Boolean, default=False)
    can_view_all_docs = db.Column(db.Boolean, default=False)

    users = db.relationship("User", back_populates="role")


class Department(BaseModel):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(256), nullable=False)
    name_en = db.Column(db.String(256), nullable=True) # 💡 增加英文名
    parent_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    level = db.Column(db.Integer, default=1)

    parent = db.relationship("Department", remote_side=[id], backref=db.backref("children", lazy="dynamic"))
    users = db.relationship("User", back_populates="department")


class Position(BaseModel):
    __tablename__ = "positions"

    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(128), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(256), nullable=False)
    full_name_en = db.Column(db.String(256), nullable=True) # 💡 增加英文全称


class User(BaseModel):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    employee_no = db.Column(db.String(64), unique=True, nullable=False, index=True)
    last_name = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(128), nullable=False)
    patronymic = db.Column(db.String(128), default="")
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(32), default="")
    phone = db.Column(db.String(64), default="")
    email = db.Column(db.String(128), default="")
    avatar_url = db.Column(db.String(512), default="")
    login_name = db.Column(db.String(128), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    position_short = db.Column(db.String(128), default="")
    manager_employee_no = db.Column(db.String(64), default="")
    is_manager = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    # Status: active, pending_dept, pending_admin, rejected
    registration_status = db.Column(db.String(32), default="active", index=True)

    department = db.relationship("Department", back_populates="users")
    role = db.relationship("Role", back_populates="users")
    documents_owned = db.relationship(
        "Document", back_populates="owner", foreign_keys="Document.owner_id"
    )

    def display_name(self) -> str:
        parts = [self.last_name, self.first_name]
        return " ".join(p for p in parts if p)

    @property
    def role_title(self) -> str:
        if self.is_super_admin:
            return "系统管理员"
        if self.role:
            return self.role.name
        return "部门经理" if self.is_manager else "普通员工"

    @property
    def role_level(self) -> int:
        if self.is_super_admin:
            return 100
        if self.role:
            return self.role.level
        return 50 if self.is_manager else 10

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        if not self.password_hash: # For legacy seeded users or direct DB adds
            return True 
        return check_password_hash(self.password_hash, password)
