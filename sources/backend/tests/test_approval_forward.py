import pytest
from app.extensions import db
from app.models.core import User, Department
from app.models.document import Document
from app.models.workflow import ApprovalFlow, ApprovalParticipant, ApprovalDecision, AuditLog
from app.models.notification import Notification
from app.services.approval_service import start_flow, apply_decision
from flask_jwt_extended import create_access_token


@pytest.fixture
def test_users(app):
    with app.app_context():
        dept = Department(name="研发部", code="DEV")
        db.session.add(dept)
        db.session.flush()

        users = []
        for i in range(1, 5):
            u = User(
                employee_no=f"EMP00{i}",
                login_name=f"user{i}",
                first_name=f"三{i}",
                last_name="张",
                department_id=dept.id,
                registration_status="active",
            )
            u.set_password("123456")
            db.session.add(u)
            users.append(u)

        db.session.commit()
        return [u.id for u in users]


def test_approval_forward_sequential_flow(app, test_users):
    with app.app_context():
        u1_id, u2_id, u3_id, u4_id = test_users
        
        # 1. Create doc
        doc = Document(
            title="测试流转文档",
            owner_id=u1_id,
            status="draft",
            doc_number="DOC2026001",
        )
        db.session.add(doc)
        db.session.commit()

        # 2. Start approval: u2 (step 1), u3 (step 2)
        flow = start_flow(doc, "sequential", [u2_id, u3_id])
        db.session.commit()

        assert flow.status == "active"
        assert flow.current_order == 1
        assert doc.status == "in_approval"
        assert len(flow.participants) == 2

        # 3. u2 decides to "forward" to u4
        p_u2 = next(p for p in flow.participants if p.user_id == u2_id)
        apply_decision(p_u2, "forward", "初步审核通过，流转给u4复审", doc, target_user_id=u4_id)
        db.session.commit()

        # Check flow state
        flow = db.session.get(ApprovalFlow, flow.id)
        assert flow.status == "active"
        assert flow.current_order == 2
        assert doc.status == "in_approval"

        # Check participants
        parts = ApprovalParticipant.query.filter_by(flow_id=flow.id).order_by(ApprovalParticipant.step_order).all()
        assert len(parts) == 3
        
        # Step 1: u2 (forward)
        assert parts[0].user_id == u2_id
        assert parts[0].step_order == 1
        assert parts[0].decision.decision == "forward"
        assert parts[0].decision.reason == "初步审核通过，流转给u4复审"

        # Step 2: u4 (pending)
        assert parts[1].user_id == u4_id
        assert parts[1].step_order == 2
        assert parts[1].decision is None

        # Step 3: u3 (shifted to step 3)
        assert parts[2].user_id == u3_id
        assert parts[2].step_order == 3
        assert parts[2].decision is None

        # 4. u4 approves
        apply_decision(parts[1], "approve", "u4核对无误", doc)
        db.session.commit()

        flow = db.session.get(ApprovalFlow, flow.id)
        assert flow.status == "active"
        assert flow.current_order == 3
        assert doc.status == "in_approval"

        # 5. u3 (final approver) approves
        apply_decision(parts[2], "approve", "u3终审同意", doc)
        db.session.commit()

        flow = db.session.get(ApprovalFlow, flow.id)
        assert flow.status == "completed"
        assert doc.status == "approved"


def test_approval_forward_then_reject(app, test_users):
    with app.app_context():
        u1_id, u2_id, u3_id, u4_id = test_users
        
        doc = Document(
            title="测试驳回文档",
            owner_id=u1_id,
            status="draft",
            doc_number="DOC2026002",
        )
        db.session.add(doc)
        db.session.commit()

        flow = start_flow(doc, "sequential", [u2_id])
        db.session.commit()

        # u2 forwards to u4
        p_u2 = flow.participants[0]
        apply_decision(p_u2, "forward", "转交u4", doc, target_user_id=u4_id)
        db.session.commit()

        # u4 rejects
        p_u4 = next(p for p in flow.participants if p.user_id == u4_id)
        apply_decision(p_u4, "reject", "资料不完整，驳回", doc)
        db.session.commit()

        flow = db.session.get(ApprovalFlow, flow.id)
        assert flow.status == "rejected"
        assert doc.status == "rejected"


def test_approval_forward_api_endpoint(client, app, test_users):
    with app.app_context():
        u1_id, u2_id, u3_id, u4_id = test_users
        u2 = db.session.get(User, u2_id)

        token = create_access_token(identity=str(u2.id))

        doc = Document(
            title="API测试文档",
            owner_id=u1_id,
            status="draft",
            doc_number="DOC2026003",
        )
        db.session.add(doc)
        db.session.commit()

        flow = start_flow(doc, "sequential", [u2_id])
        db.session.commit()

        p_u2 = flow.participants[0]

        # Call API to forward
        resp = client.post(
            f"/api/approvals/participants/{p_u2.id}/decision",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "decision": "forward",
                "target_user_id": u4_id,
                "reason": "请u4核对"
            }
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True

        # Verify Notifications were generated
        notif_u4 = Notification.query.filter_by(user_id=u4_id).first()
        assert notif_u4 is not None
        assert "待审批(流转)" in notif_u4.title

        notif_owner = Notification.query.filter_by(user_id=u1_id).first()
        assert notif_owner is not None
        assert "审批流转进度" in notif_owner.title

        # Verify AuditLog
        audit = AuditLog.query.filter_by(document_id=doc.id, action="FORWARD_APPROVAL").first()
        assert audit is not None
        assert "同意并流转" in audit.summary

        # Call GET /api/approvals/handled for u2
        h_resp = client.get(
            "/api/approvals/handled",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert h_resp.status_code == 200
        h_data = h_resp.get_json()
        assert h_data["total"] >= 1
        assert h_data["stats"]["forwarded"] >= 1
        assert h_data["items"][0]["my_decision"] == "forward"
        assert h_data["items"][0]["my_reason"] == "请u4核对"
