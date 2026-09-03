import pytest
import io
import json
from app import create_app, db
from app.config import Config
from app.models.core import User, Department
from app.models.document import Document, DocumentVersion
from app.services.spreadsheet_service import parse_excel_to_spreadsheet_json, export_spreadsheet_json_to_excel_bytes


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


def test_spreadsheet_creation_and_export(app, client):
    with app.app_context():
        user = User.query.filter_by(login_name="admin").first()
        if not user:
            user = User(login_name="admin", employee_no="ADM001", is_super_admin=True)
            user.set_password("Admin123!")
            db.session.add(user)
            db.session.commit()
        else:
            user.set_password("Admin123!")
            db.session.commit()

        # Login
        login_res = client.post("/api/auth/login", json={"login_name": "admin", "password": "Admin123!"})
        assert login_res.status_code == 200
        token = login_res.json["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Spreadsheet Document
        create_res = client.post(
            "/api/documents",
            headers=headers,
            json={"title": "Q3 Financial Plan", "doc_type": "spreadsheet"}
        )
        assert create_res.status_code == 201
        doc_data = create_res.json
        assert doc_data["title"] == "Q3 Financial Plan"
        assert doc_data["doc_type"] == "spreadsheet"
        doc_id = doc_data["id"]

        # Check in DB
        doc = Document.query.get(doc_id)
        assert doc is not None
        assert doc.doc_type == "spreadsheet"
        ver = doc.current_version
        assert ver is not None
        parsed_content = json.loads(ver.content_json)
        assert parsed_content["type"] == "spreadsheet"
        assert len(parsed_content["sheets"]) >= 1

        # 2. Update Content
        sample_sheet_data = {
            "type": "spreadsheet",
            "activeSheetId": "sheet_1",
            "sheets": [
                {
                    "id": "sheet_1",
                    "name": "Budget",
                    "rowCount": 20,
                    "colCount": 10,
                    "cells": {
                        "0_0": {"v": "Item", "m": "Item", "t": "s"},
                        "0_1": {"v": "Cost", "m": "Cost", "t": "s"},
                        "1_0": {"v": "Server", "m": "Server", "t": "s"},
                        "1_1": {"v": 5000, "m": "5000", "t": "n"},
                        "2_0": {"v": "Domain", "m": "Domain", "t": "s"},
                        "2_1": {"v": 100, "m": "100", "t": "n"},
                        "3_0": {"v": "Total", "m": "Total", "t": "s"},
                        "3_1": {"v": 5100, "m": "5100", "f": "=SUM(B2:B3)", "t": "f"},
                    },
                    "styles": {
                        "0_0": {"bl": 1, "bg": "#EFEFEF"},
                        "0_1": {"bl": 1, "bg": "#EFEFEF"},
                        "3_0": {"bl": 1},
                    },
                    "images": [],
                    "mergedCells": [],
                    "columnWidths": {"0": 120, "1": 100},
                    "rowHeights": {"0": 25}
                }
            ]
        }
        patch_res = client.patch(
            f"/api/documents/{doc_id}",
            headers=headers,
            json={"content_json": json.dumps(sample_sheet_data)}
        )
        assert patch_res.status_code == 200

        # 3. Export XLSX
        export_res = client.get(f"/api/documents/{doc_id}/export.xlsx", headers=headers)
        assert export_res.status_code == 200
        assert export_res.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        xlsx_bytes = export_res.data
        assert len(xlsx_bytes) > 0

        # 4. Import the exported XLSX back
        import_res = client.post(
            "/api/documents/import-excel",
            headers=headers,
            data={
                "file": (io.BytesIO(xlsx_bytes), "Imported_Budget.xlsx"),
                "title": "Imported Budget"
            },
            content_type="multipart/form-data"
        )
        assert import_res.status_code == 201
        imported_doc = import_res.json
        assert imported_doc["title"] == "Imported Budget"
        assert imported_doc["doc_type"] == "spreadsheet"
