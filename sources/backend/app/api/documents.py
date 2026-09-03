"""Documents REST API."""
from __future__ import annotations

import base64
import json
import os
import re
import uuid
from datetime import datetime

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from sqlalchemy import or_, select

from app.models import (
    ApprovalFlow,
    Document,
    DocumentPermission,
    DocumentVersion,
    User,
)
from app.models.workflow import ApprovalParticipant, ApprovalDecision
from app.services.approval_service import start_flow
from app.services.diff_service import diff_html, blame_html, side_by_side_diff
from app.services.document_access import (
    user_can_comment,
    user_can_edit_content,
    user_can_edit_metadata,
    user_can_view_document,
    user_can_manage_permissions,
    user_effective_document_role,
)
from app.services.document_state import VALID_STATUSES
from app.services.export_service import export_docx_bytes, export_pdf_bytes
from app.services.ai_service import AIService
from app.services.vector_store import upsert_document
from app.utils.auth import current_user
from app.utils.audit import audit_log_required
from app.utils.background import run_in_background, submit_async_task

from app.utils.text import extract_text_from_tiptap

bp = Blueprint("documents", __name__)

@bp.get("/tasks/<task_id>")
@jwt_required()
def check_task_status(task_id: str):
    from app.utils.background import get_task_status
    status = get_task_status(task_id)
    if not status:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(status)

def _async_parse_and_vectorize_pdf(task_id: str, app, doc_id: int, file_path: str):
    from app.utils.background import update_task
    import os
    import time
    
    update_task(task_id, progress=10, message="Extracting text from PDF...")
    
    with app.app_context():
        doc = Document.get_by_id_or_number(doc_id)
        if not doc:
            update_task(task_id, progress=100, status="failed", message="Document not found", error="Document not found")
            db.session.remove()
            return
            
        doc_title = doc.title
        
        # 1. Extract text using pypdf
        text_content = ""
        try:
            if os.path.exists(file_path):
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                pages_text = []
                num_pages = len(reader.pages)
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
                    # Update progress during extraction (10% to 50%)
                    current_progress = 10 + int((idx + 1) / num_pages * 40)
                    update_task(task_id, progress=current_progress, message=f"Extracting page {idx+1}/{num_pages}...")
                text_content = "\n".join(pages_text)
            else:
                text_content = doc_title
        except Exception as e:
            print(f"[Background Task] PDF text extraction error: {e}")
            text_content = doc_title
            
        if not text_content:
            text_content = doc_title
            
        # Release DB session before slower RAG operations
        db.session.remove()
        
        # 2. Vector DB Upsert
        update_task(task_id, progress=60, message="Generating document vectors...")
        try:
            from app.services.vector_store import upsert_document
            upsert_document(doc_id, doc_title, text_content)
        except Exception as e:
            print(f"[Background Task] Vector DB upsert error: {e}")
            
        # 3. AI Metadata
        update_task(task_id, progress=80, message="Generating AI summary and tags...")
        try:
            from app.services.ai_service import AIService
            meta = AIService.generate_metadata(text_content)
            
            # Re-fetch document and save metadata
            doc_update = Document.get_by_id_or_number(doc_id)
            if doc_update:
                doc_update.summary = meta.get("summary", "")
                doc_update.tags = meta.get("tags", "")
                doc_update.category = meta.get("category", "")
                
                # Save extracted text to current_version.content_json as TipTap structure
                if doc_update.current_version and text_content:
                    tiptap_content = {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": line}]
                            } for line in text_content.split("\n") if line.strip()
                        ]
                    }
                    doc_update.current_version.content_json = json.dumps(tiptap_content)
                    
                db.session.commit()
        except Exception as e:
            print(f"[Background Task] AI Metadata generation error: {e}")
            
        db.session.remove()
        update_task(task_id, progress=100, status="completed", message="Successfully processed document", result={"document_id": doc_id})

def _async_generate_diff_task(task_id: str, content_a: str, content_b: str, mode: str):
    from app.utils.background import update_task
    from app.services.diff_service import side_by_side_diff, diff_html
    
    update_task(task_id, progress=30, message="Calculating differences...")
    try:
        if mode == "side_by_side":
            html_data = side_by_side_diff(content_a, content_b)
        else:
            html_data = diff_html(content_a, content_b)
            
        update_task(task_id, progress=100, status="completed", message="Comparison complete", result={"html": html_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_task(task_id, progress=100, status="failed", message=f"Diff generation failed: {str(e)}", error=str(e))


# Cooldown tracker: doc_id -> last update epoch time
# Prevents AI metadata from being triggered on every autosave (every 2s)
_metadata_cooldown: dict = {}  # {doc_id: last_run_timestamp}
_METADATA_COOLDOWN_SECONDS = 300  # 5 minutes

def _trigger_metadata_update(app, doc_id: int):
    """Background task to generate metadata and update vector DB."""
    import time
    now = time.time()
    last_run = _metadata_cooldown.get(doc_id, 0)
    if now - last_run < _METADATA_COOLDOWN_SECONDS:
        print(f"[Background] Skipping metadata update for doc {doc_id} (cooldown: {int(_METADATA_COOLDOWN_SECONDS - (now - last_run))}s remaining)")
        return
    _metadata_cooldown[doc_id] = now

    with app.app_context():
        doc = Document.get_by_id_or_number(doc_id)
        if not doc or not doc.current_version:
            db.session.remove()
            return
        
        # 1. Extract text
        ver = doc.current_version
        text_content = ""
        doc_title = doc.title
        if doc.doc_type == "pdf" and ver.file_path:
            # We can't easily read PDF text here unless we have PyMuPDF, so we just use the title or fake it
            text_content = doc_title
        else:
            try:
                cj = json.loads(ver.content_json) if isinstance(ver.content_json, str) else ver.content_json
                text_content = extract_text_from_tiptap(cj)
            except Exception:
                text_content = doc_title
                
        # 🔑 IMPORTANT: Release DB connection back to the pool before slow network IO!
        db.session.remove()
                
        # 2. Vector DB Upsert
        if text_content:
            upsert_document(doc_id, doc_title, text_content)
            
            # 3. AI Metadata (Summary, Tags) -> This takes 10+ seconds
            meta = AIService.generate_metadata(text_content)
            
            # Re-fetch document in a new, brief transaction
            doc_update = Document.get_by_id_or_number(doc_id)
            if doc_update:
                doc_update.summary = meta.get("summary", "")
                doc_update.tags = meta.get("tags", "")
                doc_update.category = meta.get("category", "")
                db.session.commit()
                print(f"[Background] Updated metadata for doc {doc_id}")
            
            db.session.remove()



def _doc_to_summary(doc: Document, user: User) -> dict:
    ver = doc.current_version
    owner_name = None
    owner_department = None
    if doc.owner:
        owner_name = f"{doc.owner.last_name} {doc.owner.first_name}".strip()
        if doc.owner.department:
            owner_department = doc.owner.department.name
            owner_department_en = doc.owner.department.name_en
        else:
            owner_department_en = None
    # Check if current user is a pending approver for this document
    can_approve = False
    pending_participant_id = None
    if doc.status == "in_approval":
        flow = ApprovalFlow.query.filter_by(document_id=doc.id, status="active").first()
        if flow:
            # Find the participant for current user
            participant = ApprovalParticipant.query.filter_by(
                flow_id=flow.id, 
                user_id=user.id
            ).filter(ApprovalParticipant.id.not_in(
                select(ApprovalDecision.participant_id)
            )).first()
            
            if participant:
                # Also check if it's their turn for sequential
                if flow.flow_type == "parallel" or participant.step_order == flow.current_order:
                    can_approve = True
                    pending_participant_id = participant.id

    return {
        "id": doc.id,
        "doc_number": doc.doc_number or f"{doc.created_at.strftime('%Y%m%d') if doc.created_at else '00000000'}{str(doc.id).zfill(3)}",
        "title": doc.title,
        "status": doc.status,
        "owner_id": doc.owner_id,
        "owner_name": owner_name,
        "owner_department": owner_department,
        "owner_department_en": owner_department_en,
        "is_owner": doc.owner_id == user.id,
        "my_role": user_effective_document_role(user, doc),
        "created_at": doc.created_at.isoformat() + "Z" if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() + "Z" if doc.updated_at else None,
        "current_version_id": doc.current_version_id,
        "version_no": ver.version_no if ver else None,
        "can_view": True,
        "can_edit": user_can_edit_content(user, doc),
        "can_comment": user_can_comment(user, doc),
        "can_manage_permissions": user_can_manage_permissions(user, doc),
        "is_public": doc.is_public,
        "can_approve": can_approve,
        "pending_participant_id": pending_participant_id,
        "doc_type": doc.doc_type,
        "file_path": ver.file_path if ver else None,
        "space_ids": [s.id for s in doc.spaces],
        "space_names": [s.name for s in doc.spaces],
    }

@bp.get("/tree")
@jwt_required()
def list_document_tree():
    """Return documents grouped by spaces in a hierarchical tree format."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    from app.models.space import Space
    from app.models.core import Department
    from app.models.document import document_spaces
    
    spaces = Space.query.all()
    depts = Department.query.all()
    
    tree = []
    
    # 1. Spaces (Project/Topic Groups)
    for s in spaces:
        docs = db.session.query(Document).join(document_spaces).filter(
            document_spaces.c.space_id == s.id,
            Document.is_template == False,
            Document.deleted_at == None
        )
        if not user.is_super_admin:
            docs = docs.filter(or_(
                Document.owner_id == user.id,
                Document.is_public == True
            ))
        docs = docs.all()
        
        doc_map = {d.id: {
            "id": d.id,
            "title": d.title,
            "status": d.status,
            "parent_id": d.parent_id,
            "children": []
        } for d in docs}
        
        roots = []
        for d_id, d_data in doc_map.items():
            parent_id = d_data["parent_id"]
            if parent_id and parent_id in doc_map:
                doc_map[parent_id]["children"].append(d_data)
            else:
                roots.append(d_data)
                
        tree.append({
            "id": f"space_{s.id}",
            "space_id": s.id,
            "name": s.name,
            "name_en": s.name_en,
            "is_space": True,
            "children": roots
        })

    # 2. Departments (Organizational Groups)
    for dpt in depts:
        # Show documents owned by users in this department that are NOT in a space
        # and are either public or owned by current user
        conditions = [
            User.department_id == dpt.id,
            ~Document.id.in_(db.session.query(document_spaces.c.document_id)),
            Document.is_template == False,
            Document.deleted_at == None
        ]
        if not user.is_super_admin:
            conditions.append(or_(
                Document.owner_id == user.id,
                Document.is_public == True
            ))
            
        docs = Document.query.join(User).filter(*conditions).all()

        if not docs and dpt.id != user.department_id and not user.is_super_admin:
            continue

        doc_map = {d.id: {
            "id": d.id,
            "title": d.title,
            "status": d.status,
            "parent_id": d.parent_id,
            "children": []
        } for d in docs}
        
        roots = []
        for d_id, d_data in doc_map.items():
            parent_id = d_data["parent_id"]
            if parent_id and parent_id in doc_map:
                doc_map[parent_id]["children"].append(d_data)
            else:
                roots.append(d_data)

        tree.append({
            "id": f"dept_{dpt.id}",
            "name": dpt.name,
            "name_en": dpt.name_en,
            "is_dept": True,
            "is_space": True, # Use space icon for departments too
            "children": roots
        })
        
    # 2. Unassigned Documents
    unassigned_conditions = [
        Document.is_template == False,
        Document.deleted_at == None
    ]
    if not user.is_super_admin:
        unassigned_conditions.append(or_(
            Document.owner_id == user.id,
            Document.is_public == True
        ))
    
    # Documents without any spaces in junction table
    from app.models.document import document_spaces
    unassigned_docs = Document.query.filter(*unassigned_conditions).filter(
        ~Document.id.in_(db.session.query(document_spaces.c.document_id))
    ).all()
    
    return jsonify({"items": tree})

@bp.get("/stats")
@jwt_required()
def get_stats():
    """Return system-wide document statistics for AI or dashboard."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    # 💡 Filter count based on user role
    q = Document.query.filter(Document.deleted_at == None, Document.is_template == False)
    
    # 💡 Align with visibility logic from list_documents
    if user.is_super_admin:
        pass
    else:
        # Get permission IDs and flow IDs
        from sqlalchemy import select
        perm_ids = [r[0] for r in db.session.query(DocumentPermission.document_id).filter_by(user_id=user.id).all()]
        flow_ids = [r[0] for r in db.session.query(ApprovalFlow.document_id)\
                   .join(ApprovalParticipant, ApprovalParticipant.flow_id == ApprovalFlow.id)\
                   .filter(ApprovalParticipant.user_id == user.id).all()]
        
        # 💡 Secure permission union: consistent with dashboard.py
        final_cond = or_(
            Document.owner_id == user.id,
            Document.is_public == True,
            Document.id.in_(perm_ids),
            Document.id.in_(flow_ids)
        )
        
        if user.is_manager and user.department_id:
            dept_users = select(User.id).where(User.department_id == user.department_id).scalar_subquery()
            final_cond = or_(final_cond, Document.owner_id.in_(dept_users))
            
        q = q.filter(final_cond)

    total_count = q.count()
    owned_count = Document.query.filter_by(owner_id=user.id, is_template=False, deleted_at=None).count()

    return jsonify({
        "total_count": total_count,
        "owned_count": owned_count,
        "is_admin": user.is_super_admin
    })

@bp.get("")
@jwt_required()
def list_documents():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    scope = request.args.get("scope")
    space_id = request.args.get("space_id")
    dept_id = request.args.get("dept_id")
    status_filter = request.args.get("status")
    doc_type_filter = request.args.get("doc_type")
    on_chain = request.args.get("on_chain")

    if not scope:
        scope = "all"
    
    # Debug Probe
    print(f"[DEBUG] User {user.id} ({user.login_name}) listing docs with scope={scope}, space_id={space_id}")

    q = Document.query.filter(Document.is_template == False, Document.deleted_at == None)
    
    search = request.args.get("search")
    if search:
        q = q.filter(Document.title.ilike(f"%{search}%"))

    if on_chain == "true":
        q = q.filter(Document.tx_hash != None)
    
    # ── Admin Super Access ────────────────────────────────────────────────
    # If admin, show everything by default unless a specific space is filtered
    if user.is_super_admin and scope == "all":
        pass 
    else:
        if scope == "approved":
            q = q.filter(Document.status == "approved")
        elif scope == "collab":
            # 获取用户参与或有权限的 ID 列表
            perm_ids = [r[0] for r in db.session.query(DocumentPermission.document_id).filter_by(user_id=user.id).all()]
            flow_ids = [r[0] for r in db.session.query(ApprovalFlow.document_id)\
                       .join(ApprovalParticipant, ApprovalParticipant.flow_id == ApprovalFlow.id)\
                       .filter(ApprovalParticipant.user_id == user.id).all()]
            
            q = q.filter(
                or_(
                    Document.id.in_(perm_ids),
                    Document.id.in_(flow_ids),
                )
            ).filter(Document.owner_id != user.id)
        elif scope == "department":
            if user.department_id:
                dept_users = select(User.id).where(User.department_id == user.department_id)
                q = q.filter(Document.owner_id.in_(dept_users))
            else:
                q = q.filter(Document.id == -1)
        elif scope == "all":
            perm_ids = [r[0] for r in db.session.query(DocumentPermission.document_id).filter_by(user_id=user.id).all()]
            flow_ids = [r[0] for r in db.session.query(ApprovalFlow.document_id)\
                       .join(ApprovalParticipant, ApprovalParticipant.flow_id == ApprovalFlow.id)\
                       .filter(ApprovalParticipant.user_id == user.id).all()]
            
            # 💡 Secure permission union
            final_cond = (Document.owner_id == user.id) | (Document.is_public == True)
            if perm_ids:
                final_cond |= Document.id.in_(perm_ids)
            if flow_ids:
                final_cond |= Document.id.in_(flow_ids)
            
            if user.is_manager and user.department_id:
                dept_users = select(User.id).where(User.department_id == user.department_id)
                final_cond |= Document.owner_id.in_(dept_users)
                
            q = q.filter(final_cond)
        else:  # scope == "mine"
            q = q.filter(Document.owner_id == user.id)

    # Standard filtering for all users (including admin)
    if status_filter:
        if status_filter not in VALID_STATUSES:
            return jsonify({"error": "invalid status filter"}), 400
        q = q.filter(Document.status == status_filter)

    if doc_type_filter:
        q = q.filter(Document.doc_type == doc_type_filter)

    # Re-apply space filter at the end
    if space_id:
        from app.models.document import document_spaces
        if space_id == "unassigned":
            q = q.filter(~Document.id.in_(db.session.query(document_spaces.c.document_id)))
        else:
            q = q.join(document_spaces).filter(document_spaces.c.space_id == space_id)

    if dept_id:
        from app.models.document import document_spaces
        q = q.join(User).filter(User.department_id == dept_id).filter(
            ~Document.id.in_(db.session.query(document_spaces.c.document_id))
        )

    try:
        docs = q.order_by(Document.updated_at.desc()).all()
        print(f"[DEBUG] Query found {len(docs)} documents")
        return jsonify({"items": [_doc_to_summary(d, user) for d in docs]})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.post("")
@jwt_required()
def create_document():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled").strip()[:512]
    space_id = data.get("space_id")
    doc_type = (data.get("doc_type") or "rich_text").strip()
    
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import func
    import random
    import time
    
    doc = None
    for attempt in range(10):
        db.session.rollback()
        today_str = datetime.now().strftime("%Y%m%d")
        max_doc = db.session.query(func.max(Document.doc_number)).filter(
            Document.doc_number.like(f"{today_str}%")
        ).scalar()
        if max_doc:
            try:
                last_seq = int(max_doc[8:])
                doc_number = f"{today_str}{str(last_seq + 1).zfill(3)}"
            except:
                doc_number = f"{today_str}001"
        else:
            doc_number = f"{today_str}001"
            
        try:
            doc = Document()
            doc.owner_id = user.id
            doc.title = title
            doc.status = "draft"
            doc.doc_number = doc_number
            doc.doc_type = doc_type
            if space_id:
                from app.models.space import Space
                sp = db.session.get(Space, space_id)
                if sp:
                    doc.spaces.append(sp)
                    
            db.session.add(doc)
            db.session.flush()
            
            ver = DocumentVersion()
            ver.document_id = doc.id
            ver.version_no = 1
            if doc_type == "spreadsheet":
                ver.content_json = DocumentVersion.default_spreadsheet_json()
            else:
                ver.content_json = DocumentVersion.default_content_json()
            ver.created_by_id = user.id
            db.session.add(ver)
            db.session.flush()
            doc.current_version_id = ver.id
            
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == 9:
                return jsonify({"error": "Failed to generate a unique document number due to high concurrency"}), 500
            time.sleep(random.uniform(0.01, 0.05))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to create document: {str(e)}"}), 500
            
    # Trigger background updates
    from flask import current_app
    app_obj = current_app._get_current_object()
    run_in_background(_trigger_metadata_update, app_obj, doc.id)
    
    return jsonify(_doc_to_summary(doc, user)), 201


@bp.post("/import-pdf")
@jwt_required()
def import_pdf():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400
    
    title = request.form.get("title") or file.filename
    space_id = request.form.get("space_id")
    
    # Save file
    filename = f"{uuid.uuid4()}.pdf"
    
    from flask import current_app
    storage_base = os.environ.get("STORAGE_PATH", current_app.root_path)
    upload_dir = os.path.join(storage_base, "static", "uploads", "pdfs")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    
    dest_path = os.path.join(upload_dir, filename)
    file.save(dest_path)
    
    # Relative URL for frontend
    relative_path = f"/static/uploads/pdfs/{filename}"
    
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import func
    import random
    import time
    
    doc = None
    for attempt in range(10):
        db.session.rollback()
        today_str = datetime.now().strftime("%Y%m%d")
        max_doc = db.session.query(func.max(Document.doc_number)).filter(
            Document.doc_number.like(f"{today_str}%")
        ).scalar()
        if max_doc:
            try:
                last_seq = int(max_doc[8:])
                doc_number = f"{today_str}{str(last_seq + 1).zfill(3)}"
            except:
                doc_number = f"{today_str}001"
        else:
            doc_number = f"{today_str}001"
            
        try:
            doc = Document()
            doc.owner_id = user.id
            doc.title = title
            doc.status = "draft"
            doc.doc_number = doc_number
            doc.space_id = space_id if space_id and space_id != "unassigned" else None
            doc.doc_type = "pdf"
            db.session.add(doc)
            db.session.flush()
            
            ver = DocumentVersion()
            ver.document_id = doc.id
            ver.version_no = 1
            ver.file_path = relative_path
            ver.created_by_id = user.id
            db.session.add(ver)
            db.session.flush()
            doc.current_version_id = ver.id
            
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == 9:
                return jsonify({"error": "Failed to generate a unique document number due to high concurrency"}), 500
            time.sleep(random.uniform(0.01, 0.05))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
            
    # Trigger background updates
    from flask import current_app
    app_obj = current_app._get_current_object()
    task_id = submit_async_task(
        "import_pdf",
        _async_parse_and_vectorize_pdf,
        app_obj,
        doc.id,
        dest_path
    )
    
    return jsonify({
        **_doc_to_summary(doc, user),
        "task_id": task_id
    }), 201


@bp.post("/import-excel")
@jwt_required()
def import_excel():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".xlsx", ".xls", ".csv"]:
        return jsonify({"error": "Only .xlsx, .xls and .csv files are allowed"}), 400
    
    title = request.form.get("title") or os.path.splitext(file.filename)[0]
    space_id = request.form.get("space_id")
    
    from flask import current_app
    storage_base = os.environ.get("STORAGE_PATH", current_app.root_path)
    upload_dir = os.path.join(storage_base, "static", "uploads", "excel")
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(upload_dir, filename)
    file.save(dest_path)
    
    from app.services.spreadsheet_service import parse_excel_to_spreadsheet_json
    parsed_json = parse_excel_to_spreadsheet_json(dest_path)
    
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import func
    import random
    import time
    
    doc = None
    for attempt in range(10):
        db.session.rollback()
        today_str = datetime.now().strftime("%Y%m%d")
        max_doc = db.session.query(func.max(Document.doc_number)).filter(
            Document.doc_number.like(f"{today_str}%")
        ).scalar()
        if max_doc:
            try:
                last_seq = int(max_doc[8:])
                doc_number = f"{today_str}{str(last_seq + 1).zfill(3)}"
            except:
                doc_number = f"{today_str}001"
        else:
            doc_number = f"{today_str}001"
            
        try:
            doc = Document()
            doc.owner_id = user.id
            doc.title = title
            doc.status = "draft"
            doc.doc_number = doc_number
            doc.doc_type = "spreadsheet"
            if space_id and space_id != "unassigned":
                from app.models.space import Space
                sp = db.session.get(Space, space_id)
                if sp:
                    doc.spaces.append(sp)
                    
            db.session.add(doc)
            db.session.flush()
            
            ver = DocumentVersion()
            ver.document_id = doc.id
            ver.version_no = 1
            ver.content_json = parsed_json
            ver.file_path = f"/static/uploads/excel/{filename}"
            ver.created_by_id = user.id
            db.session.add(ver)
            db.session.flush()
            doc.current_version_id = ver.id
            
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == 9:
                return jsonify({"error": "Failed to generate a unique document number due to high concurrency"}), 500
            time.sleep(random.uniform(0.01, 0.05))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to create document: {str(e)}"}), 500

    return jsonify(_doc_to_summary(doc, user)), 201



@bp.get("/<doc_id>")
@jwt_required()
@audit_log_required("VIEW")
def get_document(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    ver = doc.current_version
    
    # Parse structured content & schema if low_code_form
    template_schema = None
    form_data = None
    if doc.template_schema:
        try:
            template_schema = json.loads(doc.template_schema) if isinstance(doc.template_schema, str) else doc.template_schema
        except Exception:
            template_schema = None
            
    if ver and ver.content_json:
        try:
            c_obj = json.loads(ver.content_json) if isinstance(ver.content_json, str) else ver.content_json
            if isinstance(c_obj, dict):
                form_data = c_obj.get("form_data")
                if not template_schema and c_obj.get("schema"):
                    template_schema = c_obj.get("schema")
        except Exception:
            pass

    # Extract detailed approval flow history & steps
    flow = ApprovalFlow.query.filter_by(document_id=doc.id).order_by(ApprovalFlow.id.desc()).first()
    approval_info = None
    if flow:
        participants_list = []
        for p in flow.participants:
            participants_list.append({
                "id": p.id,
                "user_id": p.user_id,
                "user_name": p.user.display_name() if p.user else "未知审批人",
                "department_name": p.user.department.name if (p.user and p.user.department) else None,
                "step_order": p.step_order,
                "decision": p.decision.decision if p.decision else None,
                "reason": p.decision.reason if p.decision else None,
                "decided_at": (p.decision.decided_at.isoformat() + "Z") if (p.decision and p.decision.decided_at) else None,
                "is_current_step": (flow.status == "active") and (flow.flow_type == "parallel" or p.step_order == flow.current_order) and (not p.decision)
            })
        approval_info = {
            "flow_id": flow.id,
            "flow_status": flow.status,
            "flow_type": flow.flow_type,
            "current_order": flow.current_order,
            "submitted_at": flow.created_at.isoformat() + "Z" if flow.created_at else None,
            "participants": participants_list
        }

    body = {
        **_doc_to_summary(doc, user),
        "owner_login": doc.owner.login_name if doc.owner else None,
        "page_settings_json": doc.page_settings_json,
        "content_json": ver.content_json if ver else None,
        "yjs_state_b64": base64.b64encode(ver.yjs_state).decode("ascii")
        if ver and ver.yjs_state
        else None,
        "file_path": ver.file_path if ver else None,
        "doc_type": doc.doc_type or ("low_code_form" if template_schema else "rich_text"),
        "is_low_code": bool(template_schema),
        "template_schema": template_schema,
        "form_data": form_data,
        "approval_info": approval_info
    }
    return jsonify(body)


@bp.put("/<doc_id>/form-data")
@jwt_required()
def update_document_form_data(doc_id):
    """Update form data on a low-code draft document and refresh content."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
        
    if doc.status != "draft" and not user.is_super_admin:
        return jsonify({"error": "Only draft forms can be modified"}), 400
        
    data = request.get_json(silent=True) or {}
    new_form_data = data.get("form_data", {})
    new_title = (data.get("title") or "").strip()
    
    if new_title:
        doc.title = new_title[:512]
        
    schema = None
    if doc.template_schema:
        try:
            schema = json.loads(doc.template_schema) if isinstance(doc.template_schema, str) else doc.template_schema
        except Exception:
            pass

    from app.api.templates import _generate_doc_markdown_from_form
    doc_markdown = _generate_doc_markdown_from_form(
        title=doc.title,
        form_data=new_form_data,
        schema=schema or {},
        user_name=doc.owner.display_name() if doc.owner else user.display_name(),
        dept_name=doc.owner.department.name if (doc.owner and doc.owner.department) else "未分配部门",
        doc_number=doc.doc_number or ""
    )

    ver = doc.current_version
    if ver:
        ver.content_json = json.dumps({
            "form_data": new_form_data,
            "schema": schema,
            "markdown": doc_markdown
        })
        ver.updated_at = datetime.utcnow()
    else:
        ver = DocumentVersion(
            document_id=doc.id,
            version_no=1,
            content_json=json.dumps({
                "form_data": new_form_data,
                "schema": schema,
                "markdown": doc_markdown
            }),
            created_by_id=user.id
        )
        db.session.add(ver)
        db.session.flush()
        doc.current_version_id = ver.id

    doc.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        "message": "Form data updated successfully",
        "title": doc.title,
        "form_data": new_form_data
    })


@bp.patch("/<doc_id>")
@jwt_required()
def patch_document(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data:
        if not user_can_edit_metadata(user, doc):
            return jsonify({"error": "Forbidden: cannot edit title in current state/role"}), 403
        doc.title = str(data["title"])[:512]
    if "page_settings_json" in data:
        doc.page_settings_json = data["page_settings_json"]
    if "space_id" in data or "space_ids" in data:
        from app.models.space import Space
        sids = data.get("space_ids")
        if sids is None: # Fallback to single ID
            sid = data.get("space_id")
            sids = [sid] if sid and sid != 'none' else []
        
        # Filter out invalid IDs
        valid_spaces = Space.query.filter(Space.id.in_(sids)).all() if sids else []
        doc.spaces = valid_spaces
    if "is_public" in data:
        if not user_can_manage_permissions(user, doc):
            return jsonify({"error": "Forbidden: only owner or approver (after approval) can change visibility"}), 403
        doc.is_public = bool(data["is_public"])
    doc.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_doc_to_summary(doc, user))


@bp.put("/<doc_id>/content")
@jwt_required()
def put_content(doc_id):
    """Autosave document body (TipTap JSON + optional Yjs state)."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    if not user_can_edit_content(user, doc):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    ver = doc.current_version
    if not ver:
        return jsonify({"error": "No version"}), 400

    from datetime import timedelta
    # Create new version if user changed OR 5+ minutes passed since last version creation
    time_passed = (datetime.utcnow() - ver.created_at) > timedelta(minutes=5)
    if (ver.created_by_id != user.id) or time_passed:
        new_ver = DocumentVersion()
        new_ver.document_id = doc.id
        new_ver.version_no = ver.version_no + 1
        new_ver.parent_version_id = ver.id
        new_ver.created_by_id = user.id
        new_ver.content_json = ver.content_json
        new_ver.yjs_state = ver.yjs_state
        db.session.add(new_ver)
        db.session.flush()
        doc.current_version_id = new_ver.id
        ver = new_ver

    if "content_json" in data:
        cj = data["content_json"]
        ver.content_json = json.dumps(cj) if isinstance(cj, (dict, list)) else str(cj)
    if "yjs_state_b64" in data and data["yjs_state_b64"]:
        ver.yjs_state = base64.b64decode(data["yjs_state_b64"])
    
    doc.updated_at = datetime.utcnow()
    try:
        db.session.commit()
        
        # Trigger background updates
        from flask import current_app
        app_obj = current_app._get_current_object()
        run_in_background(_trigger_metadata_update, app_obj, doc.id)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Autosave failed: {str(e)}"}), 500
        
    return jsonify({"ok": True})


@bp.delete("/<doc_id>")
@jwt_required()
@audit_log_required("DELETE")
def delete_document(doc_id):
    """Delete a draft or rejected document (only owner)."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    
    # Only owner
    if doc.owner_id != user.id:
        return jsonify({"error": "Forbidden: Only creator can delete"}), 403
    
    # Only draft, approved or rejected (basically not in_approval)
    if doc.status not in ("draft", "approved", "rejected"):
        return jsonify({"error": f"Forbidden: Cannot delete document in status {doc.status}"}), 400
    
    # Manually clear references to prevent FK issues
    from app.models.workflow import AuditLog
    from app.models.notification import Notification
    
    v_ids = [v.id for v in doc.versions]
    # 1. Clear version references in AuditLog
    if v_ids:
        db.session.query(AuditLog).filter(AuditLog.document_version_id.in_(v_ids)).update(
            {AuditLog.document_version_id: None}, synchronize_session=False
        )
        # Clear self-references in versions (parent_version_id) to avoid FK issues
        db.session.query(DocumentVersion).filter(DocumentVersion.id.in_(v_ids)).update(
            {DocumentVersion.parent_version_id: None}, synchronize_session=False
        )
    # 2. Clear document references in AuditLog
    db.session.query(AuditLog).filter(AuditLog.document_id == doc.id).update(
        {AuditLog.document_id: None}, synchronize_session=False
    )
    # 3. Clear document references in Notification
    db.session.query(Notification).filter(Notification.related_doc_id == doc.id).update(
        {Notification.related_doc_id: None}, synchronize_session=False
    )
    # 4. Clear parent_id for children
    db.session.query(Document).filter(Document.parent_id == doc.id).update(
        {Document.parent_id: None}, synchronize_session=False
    )

    # 5. Record the deletion in Audit Log
    delete_log = AuditLog()
    delete_log.user_id = user.id
    delete_log.action = 'DELETE'
    delete_log.document_id = doc.id
    delete_log.ip_address = request.remote_addr
    delete_log.summary = f"Deleted document: {doc.title} ({doc.doc_number})"
    db.session.add(delete_log)

    db.session.delete(doc)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/<doc_id>/versions")
@jwt_required()
def list_versions(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    items = []
    # Sort by version_no desc for latest first
    for v in sorted(doc.versions, key=lambda x: x.version_no, reverse=True):
        items.append(
            {
                "id": v.id,
                "version_no": v.version_no,
                "created_at": v.created_at.isoformat() + "Z" if v.created_at else None,
                "parent_version_id": v.parent_version_id,
                "created_by_id": v.created_by_id,
                "created_by_name": v.created_by.login_name if v.created_by else "System",
            }
        )
    return jsonify({"items": items})


@bp.get("/<doc_id>/versions/<int:vid>/content")
@jwt_required()
def get_version_content(doc_id, vid: int):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    v = db.session.get(DocumentVersion, vid)
    if not v or v.document_id != doc.id:
        return jsonify({"error": "Not found"}), 404
    return jsonify(
        {
            "content_json": v.content_json,
            "version_no": v.version_no,
        }
    )


@bp.get("/<doc_id>/diff")
@jwt_required()
def get_diff(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    v_from = request.args.get("from", type=int)
    v_to = request.args.get("to", type=int)
    if not v_from or not v_to:
        return jsonify({"error": "from and to version ids required"}), 400
    a = db.session.get(DocumentVersion, v_from)
    b = db.session.get(DocumentVersion, v_to)
    if not a or not b or a.document_id != doc.id or b.document_id != doc.id:
        return jsonify({"error": "Invalid versions"}), 400
    mode = request.args.get("mode", "inline")
    
    # Submit diff generation as a background task
    task_id = submit_async_task(
        "generate_diff",
        _async_generate_diff_task,
        a.content_json or "{}",
        b.content_json or "{}",
        mode
    )
    return jsonify({"task_id": task_id}), 202


@bp.get("/<doc_id>/blame")
@jwt_required()
def get_blame(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
        
    versions_data = []
    colors = ["#f87171", "#fb923c", "#fbbf24", "#34d399", "#38bdf8", "#818cf8", "#c084fc", "#f472b6"]
    author_color_map = {}
    
    for v in sorted(doc.versions, key=lambda x: x.version_no):
        author_name = "Unknown"
        if v.created_by:
            author_name = f"{v.created_by.last_name} {v.created_by.first_name}".strip() or v.created_by.login_name
            
        if author_name not in author_color_map:
            author_color_map[author_name] = colors[len(author_color_map) % len(colors)]
            
        versions_data.append({
            "version_no": v.version_no,
            "content_json": v.content_json,
            "author_name": author_name,
            "author_color": author_color_map[author_name],
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
        })
        
    html_out = blame_html(versions_data)
    legend = [{"name": k, "color": v} for k, v in author_color_map.items()]
    
    return jsonify({"html": html_out, "legend": legend})


@bp.post("/<doc_id>/permissions")
@jwt_required()
def set_permissions(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_manage_permissions(user, doc):
        return jsonify({"error": "Forbidden"}), 403
    if doc.status not in ("draft", "approved"):
        return jsonify({"error": "Permissions can only be changed while document is draft or approved"}), 400
    data = request.get_json(silent=True) or {}
    grants = data.get("grants") or []
    seen: set[int] = set()
    DocumentPermission.query.filter_by(document_id=doc.id).delete()
    for g in grants:
        uid = g.get("user_id")
        role = g.get("role")
        if doc.status == "approved" and role not in ("view", "comment"):
            continue # 已审批通过只能改查看和批注
        if doc.status == "draft" and role not in ("view", "edit", "comment"):
            # 草稿允许编辑和评论
            continue
        if not uid:
            continue
        uid_int = int(uid)
        if uid_int == user.id:
            continue
        if uid_int in seen:
            continue
        seen.add(uid_int)
        if not db.session.get(User, uid_int):
            return jsonify({"error": f"Unknown user_id: {uid_int}"}), 400
        perm = DocumentPermission()
        perm.document_id = doc.id
        perm.user_id = uid_int
        perm.role = role
        db.session.add(perm)

        # 💡 处理个人通知逻辑
        should_notify = (role == "edit") or (data.get("notify") is True)
        if should_notify:
            from app.models.notification import Notification
            from datetime import datetime, timedelta
            
            # 检查是否已有相同文档的未读协作通知
            existing = Notification.query.filter_by(
                user_id=uid_int, 
                related_doc_id=doc.id, 
                type="协作", 
                is_read=False
            ).first()
            
            if not existing:
                title = f"待编辑: {doc.title}" if role == "edit" else f"共享文档: {doc.title}"
                expires = datetime.utcnow() + timedelta(days=30)
                new_notif = Notification()
                new_notif.user_id = uid_int
                new_notif.type = "协作"
                new_notif.title = title
                new_notif.content = f"用户 {user.display_name()} 为您分配了文档的 {role} 权限。"
                new_notif.related_doc_id = doc.id
                new_notif.link_url = f"/doc/{doc.id}"
                new_notif.expires_at = expires
                db.session.add(new_notif)

    # 💡 处理“共享给所有人”的通知逻辑
    if data.get("notify") is True and data.get("is_public") is True:
        from app.models.notification import Notification
        from datetime import datetime, timedelta
        expires = datetime.utcnow() + timedelta(days=30)
        
        # 获取所有活跃用户，排除当前操作者和已通知过的用户
        all_users = User.query.filter(User.id != user.id, User.id != doc.owner_id).all()
        for u in all_users:
            if u.id in seen:
                continue
            
            # 避免重复通知
            existing = Notification.query.filter_by(
                user_id=u.id, 
                related_doc_id=doc.id, 
                type="协作", 
                is_read=False
            ).first()
            
            if not existing:
                new_notif = Notification()
                new_notif.user_id = u.id
                new_notif.type = "协作"
                new_notif.title = f"全员共享: {doc.title}"
                new_notif.content = f"用户 {user.display_name()} 已将文档共享给所有人。"
                new_notif.related_doc_id = doc.id
                new_notif.link_url = f"/doc/{doc.id}"
                new_notif.expires_at = expires
                db.session.add(new_notif)

    print(f"[DEBUG] Committing permissions for doc {doc.id}")
    db.session.commit()
    return jsonify({"ok": True})


@bp.delete("/<doc_id>/permissions/<int:grantee_id>")
@jwt_required()
def delete_permission(doc_id, grantee_id: int):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_manage_permissions(user, doc):
        return jsonify({"error": "Forbidden"}), 403
    if doc.status not in ("draft", "approved"):
        return jsonify({"error": "Permissions can only be changed while document is draft or approved"}), 400
    p = DocumentPermission.query.filter_by(
        document_id=doc.id, user_id=grantee_id
    ).first()
    if not p:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/<doc_id>/permissions")
@jwt_required()
def get_permissions(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_manage_permissions(user, doc):
        return jsonify({"error": "Not found"}), 404
    perms = DocumentPermission.query.filter_by(document_id=doc.id).all()
    return jsonify(
        {
            "items": [
                {"user_id": p.user_id, "role": p.role, "login_name": p.user.login_name}
                for p in perms
            ]
        }
    )


@bp.get("/<doc_id>/collaborators")
@jwt_required()
def get_collaborators(doc_id):
    """获取文档的协作者列表（当前有权限的用户）"""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    
    # 获取有权限的用户（包括 owner 和有权限的用户）
    collabs = []
    # 添加 owner
    if doc.owner:
        collabs.append({
            "user_id": doc.owner.id,
            "login_name": doc.owner.login_name,
            "name": doc.owner.display_name(),
            "is_owner": True
        })
    
    # 获取有权限的用户
    perms = DocumentPermission.query.filter_by(document_id=doc.id).all()
    for p in perms:
        if p.user:
            collabs.append({
                "user_id": p.user.id,
                "login_name": p.user.login_name,
                "name": p.user.display_name(),
                "role": p.role,
                "is_owner": False
            })
    
    return jsonify({"items": collabs})


@bp.get("/<doc_id>/export.docx")
@jwt_required()
@audit_log_required("EXPORT_DOCX")
def export_docx(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    ver = doc.current_version
    ps = json.loads(doc.page_settings_json) if doc.page_settings_json else None
    raw = export_docx_bytes(ver.content_json if ver else "{}", page_settings=ps)
    return Response(
        raw,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="doc_{doc_id}.docx"'},
    )


@bp.get("/<doc_id>/export.pdf")
@jwt_required()
@audit_log_required("EXPORT_PDF")
def export_pdf(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    ver = doc.current_version
    ps = json.loads(doc.page_settings_json) if doc.page_settings_json else None
    
    watermark_text = f"{user.display_name()} · {user.employee_no} · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    raw = export_pdf_bytes(ver.content_json if ver else "{}", page_settings=ps, watermark_text=watermark_text)
    return Response(
        raw,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="doc_{doc_id}.pdf"'},
    )


@bp.get("/<doc_id>/export.xlsx")
@jwt_required()
@audit_log_required("EXPORT_XLSX")
def export_xlsx(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_view_document(user, doc):
        return jsonify({"error": "Not found"}), 404
    ver = doc.current_version
    from app.services.spreadsheet_service import export_spreadsheet_json_to_excel_bytes
    raw = export_spreadsheet_json_to_excel_bytes(ver.content_json if ver else "{}")
    safe_title = re.sub(r'[^\w\-_.]', '_', doc.title) or f"doc_{doc_id}"
    return Response(
        raw,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.xlsx"'},
    )


@bp.post("/upload-image")
@jwt_required()
def upload_image():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if "file" not in request.files:
        return jsonify({"error": "No file parameter"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        return jsonify({"error": "Invalid image extension. Only jpg, png, gif, webp allowed."}), 400
        
    from flask import current_app
    # 💡 优化：从环境变量获取存储路径，方便 Docker 持久化
    storage_base = os.environ.get("STORAGE_PATH", current_app.root_path)
    save_dir = os.path.join(storage_base, "static", "images")
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    
    file.save(os.path.join(save_dir, filename))
    # 注意：URL 仍然通过 /static/images 访问，我们需要在 Web 服务器配置静态映射
    url = f"/static/images/{filename}"
    return jsonify({"url": url})


@bp.post("/upload-attachment")
@jwt_required()
def upload_attachment():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if "file" not in request.files:
        return jsonify({"error": "No file parameter"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    ext = os.path.splitext(file.filename)[1].lower()
    from flask import current_app
    storage_base = os.environ.get("STORAGE_PATH", current_app.root_path)
    save_dir = os.path.join(storage_base, "static", "attachments")
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(save_dir, filename)
    file.save(file_path)
    url = f"/static/attachments/{filename}"
    return jsonify({
        "url": url,
        "filename": filename,
        "original_name": file.filename,
        "size": os.path.getsize(file_path)
    })




@bp.post("/<doc_id>/approvals")
@jwt_required()
def start_approval(doc_id):
    user = current_user()
    doc = Document.get_by_id_or_number(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
        
    print(f"[DEBUG] Starting approval for doc {doc_id} by user {user.login_name if user else 'UNKNOWN'}. Doc Owner: {doc.owner_id}, Status: {doc.status}")
    
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    # 💡 只有草稿状态才能发起审批
    if doc.status != "draft":
        return jsonify({"error": f"Cannot start approval: Document is already in {doc.status} status."}), 400
        
    if not user_can_manage_permissions(user, doc):
        return jsonify({"error": "Forbidden: You don't have permission to start approval for this document."}), 403
    
    data = request.get_json(silent=True) or {}
    flow_type = (data.get("type") or "parallel").lower()
    ids = data.get("approvers") or []
    print(f"[DEBUG] Flow type: {flow_type}, Approver IDs: {ids}")
    
    if flow_type not in ("parallel", "sequential"):
        return jsonify({"error": "invalid flow_type"}), 400
    approvers = [int(x) for x in ids]
    
    if doc.owner_id in approvers:
        return jsonify({"error": "Owner cannot be an approver"}), 400
        
    try:
        from app.services.approval_service import start_flow
        from app.extensions import socketio
        from app.models.notification import Notification

        # 1. 核心流程：创建审批流
        flow = start_flow(doc, flow_type, approvers)
        
        # 2. 发送通知给审批人
        sender_name = user.display_name()
        for aud in approvers:
            n = Notification()
            n.user_id = aud
            n.type = "审批"
            n.title = f"待审批: {doc.title}"
            n.content = f"用户 {sender_name} 邀请您审批文档 '{doc.title}'。"
            n.related_doc_id = doc_id
            n.link_url = f"/inbox"
            db.session.add(n)
        
        db.session.commit()
        print(f"[DEBUG] Transaction committed. Flow: {flow.id}")

        # 3. 实时通知前端（💡 关键修复：扔进后台任务，绝不阻塞当前请求）
        socketio.start_background_task(
            lambda: socketio.emit(
                "status_change",
                {
                    "document_id": doc_id,
                    "status": doc.status,
                    "can_edit": False
                },
                to=f"doc_{doc_id}"
            )
        )
        
        return jsonify({
            "flow_id": flow.id, 
            "document_status": doc.status,
            "can_edit": False
        })
    except Exception as e:
        db.session.rollback()
        print(f"[DEBUG] ERROR in start_approval: {str(e)}")
        return jsonify({"error": str(e)}), 400


@bp.post("/<doc_id>/recall")
@jwt_required()
def recall_document_approval(doc_id):
    """Recall a document from approval state."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or doc.owner_id != user.id:
        return jsonify({"error": "Forbidden"}), 403
    
    from app.services.approval_service import recall_flow
    try:
        recall_flow(doc)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    db.session.commit()

    # 💡 使用后台任务发送实时状态通知，不阻塞响应
    from app.extensions import socketio
    socketio.start_background_task(
        lambda: socketio.emit(
            "status_change",
            {
                "document_id": doc.id,
                "status": doc.status,
                "can_edit": True
            },
            to=f"doc_{doc.id}"
        )
    )

    return jsonify({"ok": True, "document_status": doc.status})


@bp.post("/<doc_id>/new-version")
@jwt_required()
def new_version_after_reject(doc_id):
    """Create new version from current content when document was rejected."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc or not user_can_manage_permissions(user, doc):
        return jsonify({"error": "Forbidden"}), 403
    if doc.status != "rejected":
        return jsonify({"error": "Only rejected documents"}), 400
    old = doc.current_version
    max_no = max((v.version_no for v in doc.versions), default=0)
    ver = DocumentVersion()
    ver.document_id = doc.id
    ver.version_no = max_no + 1
    ver.content_json = old.content_json if old else DocumentVersion.default_content_json()
    ver.yjs_state = old.yjs_state if old else None
    ver.created_by_id = user.id
    ver.parent_version_id = old.id if old else None
    db.session.add(ver)
    db.session.flush()
    doc.current_version_id = ver.id
    doc.status = "draft"
    doc.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"current_version_id": ver.id, "version_no": ver.version_no})

@bp.post("/batch-delete")
@jwt_required()
def batch_delete_documents():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    doc_ids = data.get("doc_ids", [])
    
    success_count = 0
    errors = []
    
    from app.models.workflow import AuditLog
    from app.models.notification import Notification
    import traceback
    
    try:
        # Step 1: Pre-filter and collect valid docs to delete
        valid_docs = []
        for did in doc_ids:
            doc = db.session.get(Document, did)
            if not doc:
                continue
            if doc.owner_id != user.id:
                errors.append(f"Doc {did}: Forbidden")
                continue
            if doc.status not in ("draft", "approved", "rejected"):
                errors.append(f"Doc {did}: Cannot delete in status {doc.status}")
                continue
            valid_docs.append(doc)
            
        if not valid_docs:
            return jsonify({"message": "No valid documents to delete", "errors": errors})

        valid_ids = [d.id for d in valid_docs]
        
        # Step 2: Batch clear references to avoid FK issues
        # Clear versions in AuditLog
        v_ids = []
        for d in valid_docs:
            v_ids.extend([v.id for v in d.versions])
        
        if v_ids:
            db.session.query(AuditLog).filter(AuditLog.document_version_id.in_(v_ids)).update(
                {AuditLog.document_version_id: None}, synchronize_session=False
            )
            # Clear self-references in versions (parent_version_id)
            db.session.query(DocumentVersion).filter(DocumentVersion.id.in_(v_ids)).update(
                {DocumentVersion.parent_version_id: None}, synchronize_session=False
            )
        
        # Clear document references in AuditLog and Notification
        db.session.query(AuditLog).filter(AuditLog.document_id.in_(valid_ids)).update(
            {AuditLog.document_id: None}, synchronize_session=False
        )
        db.session.query(Notification).filter(Notification.related_doc_id.in_(valid_ids)).update(
            {Notification.related_doc_id: None}, synchronize_session=False
        )
        
        # Clear parent_id for children
        db.session.query(Document).filter(Document.parent_id.in_(valid_ids)).update(
            {Document.parent_id: None}, synchronize_session=False
        )
        
        # Flush these changes so the database knows references are gone
        db.session.flush()
        
        # Step 3: Delete documents and log them
        for doc in valid_docs:
            # Record deletion in audit log
            delete_log = AuditLog()
            delete_log.user_id = user.id
            delete_log.action = 'DELETE'
            delete_log.document_id = doc.id
            delete_log.ip_address = request.remote_addr
            delete_log.summary = f"Batch deleted document: {doc.title} ({doc.doc_number})"
            db.session.add(delete_log)
            
            db.session.delete(doc)
            success_count += 1
            
        db.session.commit()
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
        
    return jsonify({"message": f"Deleted {success_count} documents", "errors": errors})

@bp.post("/batch-share")
@jwt_required()
def batch_share_documents():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    doc_ids = data.get("doc_ids", [])
    is_public = data.get("is_public", False)
    
    success_count = 0
    errors = []
    
    for did in doc_ids:
        doc = db.session.get(Document, did)
        if not doc:
            continue
        
        if not user_can_manage_permissions(user, doc):
            errors.append(f"Doc {did}: Forbidden")
            continue
            
        doc.is_public = is_public
        success_count += 1
        
    db.session.commit()
    return jsonify({"message": f"Shared {success_count} documents", "errors": errors})

@bp.route('/<doc_id>/archive', methods=['POST'])
@jwt_required()
def archive_document(doc_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.get_by_id_or_number(doc_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
        
    from app.services.mock_blockchain import MockBlockchainService
    current_version = doc.current_version
    
    # 1. 算哈希
    doc_hash = MockBlockchainService.calculate_hash(current_version.content_json if current_version else '')
    
    # 2. 模拟上链
    tx_hash = MockBlockchainService.mock_notarize_to_chain()
    
    # 3. 固化凭证到 documents 主表
    doc.status = 'approved' 
    doc.file_hash = doc_hash
    doc.tx_hash = tx_hash
    db.session.commit()
    
    return jsonify({"msg": "归档并上链成功", "tx_hash": tx_hash})

@bp.route('/<doc_id>/verify', methods=['GET'])
@jwt_required()
def verify_document(doc_id):
    doc = Document.get_by_id_or_number(doc_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
        
    from app.services.mock_blockchain import MockBlockchainService
    import time
    
    current_version = doc.current_version
    
    # 重新计算当前数据库里文本的哈希
    current_hash = MockBlockchainService.calculate_hash(current_version.content_json if current_version else '')
    
    time.sleep(0.8) # 模拟正在全网广播查询的延迟
    
    # 如果还没上链，直接认为是安全的未上链状态
    if not doc.file_hash:
        return jsonify({
            "safe": True,
            "msg": "文档尚未上链存证",
            "tx_hash": "N/A"
        })

    # 核心拦截逻辑：拿现在的哈希 vs 归档时存的哈希
    if current_hash == doc.file_hash:
        return jsonify({
            "safe": True, 
            "msg": "链上指纹匹配，数据未被篡改！", 
            "tx_hash": doc.tx_hash
        })
    else:
        # ======= 新增：真正把内鬼行为写入数据库 (增加唯一性校验，防止重复计数) =======
        from app.models.workflow import AuditLog
        from flask import request
        user = current_user()
        
        # 检查是否已经针对该文档记录过拦截（防止连续点击导致次数虚高）
        exists = AuditLog.query.filter_by(document_id=doc.id, action='INTRUSION_ALERT').first()
        if not exists:
            tamper_log = AuditLog()
            tamper_log.user_id = user.id if user else None
            tamper_log.document_id = doc.id
            tamper_log.action = 'INTRUSION_ALERT'
            tamper_log.ip_address = request.remote_addr
            tamper_log.summary = '【零信任拦截】用户发起确权审计，系统比对发现底层物理数据已被未知来源非法篡改，已阻断！'
            tamper_log.is_starred = True
            db.session.add(tamper_log)
            db.session.commit()
        # ===============================================
        return jsonify({
            "safe": False, 
            "msg": "致命警告：底层数据哈希异常，文件已遭非法篡改！"
        })

@bp.post("/batch-move")
@jwt_required()
def batch_move_documents():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    doc_ids = data.get("doc_ids", [])
    space_ids = data.get("space_ids", [])
    append_mode = data.get("append", False) # Whether to add or replace
    
    if not doc_ids:
        return jsonify({"error": "No document IDs provided"}), 400
        
    from app.models.space import Space
    target_spaces = Space.query.filter(Space.id.in_(space_ids)).all() if space_ids else []
    
    docs = Document.query.filter(Document.id.in_(doc_ids)).all()
    updated_count = 0
    for doc in docs:
        if user_can_edit_metadata(user, doc):
            if append_mode:
                # Add unique spaces
                existing_ids = {s.id for s in doc.spaces}
                for ts in target_spaces:
                    if ts.id not in existing_ids:
                        doc.spaces.append(ts)
            else:
                # Replace
                doc.spaces = target_spaces
            updated_count += 1
            
    db.session.commit()
    return jsonify({"success": True, "count": updated_count})
