"""Tests for Low-Code / No-Code Form Templates & Document Generation."""
import json
import pytest
from app.extensions import db
from app.models.core import User, Department
from app.models.document import Document, DocumentVersion
from flask_jwt_extended import create_access_token


def test_low_code_template_crud_and_generation(app, client):
    with app.app_context():
        # Setup admin
        admin = User.query.filter_by(login_name="admin").first()
        if not admin:
            admin = User(login_name="admin", employee_no="ADMIN001", first_name="Sys", last_name="Admin", is_super_admin=True, is_manager=True)
            db.session.add(admin)
            db.session.commit()
        token = create_access_token(identity=str(admin.id))

        # 1. Create a Low-Code Template with Rich Form Schema
        schema = {
            "title": "项目出差与费用报销申请表",
            "description": "用于申请出差审批、日期区间、预算与凭证附件上传",
            "icon": "Tickets",
            "fields": [
                {
                    "id": "f_title",
                    "label": "出差项目名称",
                    "type": "text",
                    "required": True
                },
                {
                    "id": "f_dates",
                    "label": "出差起止日期",
                    "type": "daterange",
                    "required": True
                },
                {
                    "id": "f_times",
                    "label": "每日工作时间段",
                    "type": "timerange",
                    "required": False
                },
                {
                    "id": "f_urgent",
                    "label": "是否加急审批",
                    "type": "switch",
                    "required": False
                },
                {
                    "id": "f_rate",
                    "label": "重要评级",
                    "type": "rate",
                    "required": False
                },
                {
                    "id": "f_progress",
                    "label": "项目完成进度",
                    "type": "slider",
                    "required": False
                },
                {
                    "id": "f_files",
                    "label": "发票与差旅凭证附件",
                    "type": "attachment",
                    "required": False
                }
            ]
        }

        resp = client.post(
            "/api/templates/admin",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "项目出差与费用报销申请表",
                "description": "用于申请出差审批、日期区间、预算与凭证附件上传",
                "icon": "Tickets",
                "is_public": True,
                "template_schema": schema
            }
        )
        assert resp.status_code == 201
        tmpl_id = resp.get_json()["id"]

        # 2. Get template detail
        detail_resp = client.get(f"/api/templates/{tmpl_id}", headers={"Authorization": f"Bearer {token}"})
        assert detail_resp.status_code == 200
        detail_data = detail_resp.get_json()
        assert detail_data["is_low_code"] is True
        assert len(detail_data["template_schema"]["fields"]) == 7

        # 3. Test Form Submission -> Auto-generate Document with Rich Types
        form_data = {
            "f_title": "北京技术峰会出差及产品路演",
            "f_dates": ["2026-09-01", "2026-09-05"],
            "f_times": ["09:00", "18:00"],
            "f_urgent": True,
            "f_rate": 5,
            "f_progress": 85,
            "f_files": [
                {"name": "机票行程单.pdf", "url": "/static/attachments/ticket.pdf", "size": 102400},
                {"name": "酒店住宿发票.jpg", "url": "/static/attachments/hotel.jpg", "size": 204800}
            ]
        }
        gen_resp = client.post(
            f"/api/templates/{tmpl_id}/generate-from-form",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "form_data": form_data,
                "title": "2026秋季北京峰会出差报销单"
            }
        )
        assert gen_resp.status_code == 201
        gen_data = gen_resp.get_json()
        new_doc_id = gen_data["id"]

        # Verify generated document content formatting
        new_doc = db.session.get(Document, new_doc_id)
        assert new_doc is not None
        assert new_doc.current_version is not None
        content_obj = json.loads(new_doc.current_version.content_json)
        markdown_content = content_obj.get("markdown", "")
        
        # Verify rendered elements
        assert "2026-09-01" in markdown_content and "2026-09-05" in markdown_content
        assert "09:00" in markdown_content and "18:00" in markdown_content
        assert "✔ 是 (开启)" in markdown_content
        assert "⭐" in markdown_content
        assert "85%" in markdown_content
        assert "机票行程单.pdf" in markdown_content
        assert "酒店住宿发票.jpg" in markdown_content

        # 4. Test AI Schema Generation endpoint
        ai_resp = client.post(
            "/api/templates/ai-generate-schema",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "行政部办公用品采购申请"}
        )
        assert ai_resp.status_code == 200
        ai_data = ai_resp.get_json()
        assert "schema" in ai_data
        assert "fields" in ai_data["schema"]
