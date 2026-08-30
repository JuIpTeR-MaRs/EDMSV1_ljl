"""Approval workflow transitions."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.extensions import db
from app.models import Document
from app.models.workflow import (
    ApprovalDecision,
    ApprovalFlow,
    ApprovalParticipant,
)
from app.models.core import User


def cancel_active_flows(document_id: int) -> None:
    flows = ApprovalFlow.query.filter_by(document_id=document_id, status="active").all()
    for f in flows:
        f.status = "cancelled"


def start_flow(
    document: Document,
    flow_type: str,
    approver_user_ids: list[int],
) -> ApprovalFlow:
    """Create active approval flow; document must be draft."""
    if document.status != "draft":
        raise ValueError("Document must be draft")
    if not approver_user_ids:
        raise ValueError("At least one approver")
    print(f"[DEBUG] Cancelling active flows for doc {document.id}")
    cancel_active_flows(document.id)
    print(f"[DEBUG] Creating ApprovalFlow object for type {flow_type}")
    flow = ApprovalFlow(
        document_id=document.id,
        flow_type=flow_type,
        status="active",
        current_order=1,
    )
    db.session.add(flow)
    print("[DEBUG] Flushing flow to DB...")
    db.session.flush()
    print(f"[DEBUG] Flow ID {flow.id} flushed. Adding {len(approver_user_ids)} participants...")
    for i, uid in enumerate(approver_user_ids, start=1):
        db.session.add(
            ApprovalParticipant(flow_id=flow.id, user_id=uid, step_order=i),
        )
    print("[DEBUG] Updating document status to in_approval...")
    document.status = "in_approval"
    document.updated_at = datetime.utcnow()
    print("[DEBUG] Finalizing flush for start_flow...")
    db.session.flush()
    print("[DEBUG] start_flow logic complete.")
    return flow


def apply_decision(
    participant: ApprovalParticipant,
    decision: str,
    reason: Optional[str],
    document: Optional[Document],
    target_user_id: Optional[int] = None,
) -> None:
    if participant.flow.status != "active":
        raise ValueError("Flow not active")
    if participant.decision:
        raise ValueError("Already decided")
    flow = participant.flow
    if flow.flow_type == "sequential":
        if participant.step_order != flow.current_order:
            raise ValueError("Not your turn in sequential flow")

    new_decision = ApprovalDecision(
        participant_id=participant.id,
        decision=decision,
        reason=reason or "",
    )
    participant.decision = new_decision
    
    db.session.add(new_decision)
    db.session.flush()

    if decision == "reject":
        flow.status = "rejected"
        if document:
            document.status = "rejected"
            document.updated_at = datetime.utcnow()
        if flow.flow_type == "registration":
            user = User.query.get(flow.rel_id)
            if user:
                user.registration_status = "rejected"
        return

    if decision == "forward":
        if not target_user_id:
            raise ValueError("target_user_id is required for forward decision")
        target_user = db.session.get(User, target_user_id)
        if not target_user or target_user.registration_status != "active":
            raise ValueError("Target user does not exist or is not active")
        if target_user_id == participant.user_id:
            raise ValueError("Cannot forward to yourself")

        if flow.flow_type in ("sequential", "registration"):
            # Shift subsequent participants
            subsequent_participants = ApprovalParticipant.query.filter(
                ApprovalParticipant.flow_id == flow.id,
                ApprovalParticipant.step_order > participant.step_order
            ).all()
            for sub_p in subsequent_participants:
                sub_p.step_order += 1

            next_order = participant.step_order + 1
            new_participant = ApprovalParticipant(
                flow_id=flow.id,
                user_id=target_user_id,
                step_order=next_order,
            )
            db.session.add(new_participant)
            flow.current_order = next_order
        else:
            # Parallel flow
            new_participant = ApprovalParticipant(
                flow_id=flow.id,
                user_id=target_user_id,
                step_order=participant.step_order,
            )
            db.session.add(new_participant)

        if document:
            document.updated_at = datetime.utcnow()
        db.session.flush()
        return

    if flow.flow_type == "parallel":
        pending = [p for p in flow.participants if not p.decision]
        if not pending:
            if any(p.decision and p.decision.decision == "reject" for p in flow.participants):
                flow.status = "rejected"
                if document:
                    document.status = "rejected"
            else:
                flow.status = "completed"
                if document:
                    document.status = "approved"
        if document:
            document.updated_at = datetime.utcnow()
        return

    # sequential / registration approve
    # For registration, multiple people might be at step 1 (HR).
    # The first one to approve moves current_order to 2, effectively skipping others.
    orders = sorted({p.step_order for p in flow.participants})
    idx = orders.index(flow.current_order)
    if idx + 1 < len(orders):
        flow.current_order = orders[idx + 1]
        # Intermediate status for registration (Moving from HR to Admin)
        if flow.flow_type == "registration" and flow.current_order == 2:
            user = User.query.get(flow.rel_id)
            if user:
                user.registration_status = "pending_admin"
    else:
        flow.status = "completed"
        if document:
            document.status = "approved"
        if flow.flow_type == "registration":
            user = User.query.get(flow.rel_id)
            if user:
                user.registration_status = "active"
                # Also generate a unique employee number if it was REQ_...
                if user.employee_no.startswith("REQ_"):
                    import random
                    user.employee_no = f"E{datetime.now().year}{random.randint(1000, 9999)}"
    
    if document:
        document.updated_at = datetime.utcnow()


def recall_flow(document: Document) -> None:
    """Recall active approval and set back to draft."""
    if document.status != "in_approval":
        raise ValueError("Document is not in approval state")
    cancel_active_flows(document.id)
    document.status = "draft"
    document.updated_at = datetime.utcnow()