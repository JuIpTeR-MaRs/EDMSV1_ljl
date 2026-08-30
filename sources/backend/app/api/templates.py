"""Template Gallery & Low-Code Form Designer API — management, schema & document generation."""
import json
import re
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models.document import Document, DocumentVersion
from app.utils.auth import current_user
from app.services.ai_service import AIService

bp = Blueprint("templates", __name__)


def _can_manage_templates(user) -> bool:
    if not user:
        return False
    if user.login_name == "admin" or getattr(user, "is_super_admin", False):
        return True
    if getattr(user, "is_manager", False):
        return True
    if getattr(user, "role_level", 0) and user.role_level >= 50:
        return True
    return False


def _is_super_admin(user) -> bool:
    if not user:
        return False
    return user.login_name == "admin" or getattr(user, "is_super_admin", False)


def _safe_load_schema(schema_str):
    if not schema_str:
        return None
    if isinstance(schema_str, dict):
        return schema_str
    try:
        return json.loads(schema_str)
    except Exception:
        return None


def _generate_doc_markdown_from_form(title: str, form_data: dict, schema: dict, user_name: str, dept_name: str, doc_number: str) -> str:
    """Compose a clean, beautifully formatted Markdown document from structured form data."""
    fields = schema.get("fields", []) if schema else []
    fields_map = {f.get("id"): f for f in fields}
    
    # 1. Custom layout template support if provided
    layout_html = schema.get("layout_html") if schema else None
    if layout_html and "{{" in layout_html:
        rendered = layout_html
        for field_id, val in form_data.items():
            f_info = fields_map.get(field_id, {})
            val_str = str(val) if val is not None else ""
            rendered = rendered.replace(f"{{{{{field_id}}}}}", val_str)
            rendered = rendered.replace(f"{{{{{f_info.get('label', field_id)}}}}}", val_str)
        rendered = rendered.replace("{{doc_number}}", doc_number or "")
        rendered = rendered.replace("{{created_at}}", datetime.utcnow().strftime("%Y-%m-%d"))
        rendered = rendered.replace("{{applicant}}", user_name or "")
        rendered = rendered.replace("{{department}}", dept_name or "")
        return rendered

    # 2. Standard Responsive Markdown Document Layout
    date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"# {title}",
        "",
        f"> **单据编号**：`{doc_number}`  |  **填报时间**：{date_str}",
        f"> **填报人员**：{user_name}  |  **所属部门**：{dept_name}  |  **审批状态**：审批流转中",
        "",
        "---",
        "",
        "| 申报字段项 | 填报具体内容与凭证 |",
        "| :--- | :--- |",
    ]
    
    for field in fields:
        fid = field.get("id")
        label = field.get("label", fid)
        ftype = field.get("type", "text")
        val = form_data.get(fid)
        
        if val is None or val == "" or val == []:
            val_display = "—"
        elif ftype == "number":
            unit = field.get("unit") or ""
            val_display = f"🔢 **{val} {unit}**".strip()
        elif ftype == "amount":
            unit = field.get("unit") or "元"
            if isinstance(val, (int, float)):
                val_display = f"💰 **￥{val:,.2f} {unit}**"
            else:
                val_display = f"💰 **￥{val} {unit}**"
        elif ftype in ("select", "radio"):
            val_display = f"**{val}**"
        elif ftype == "checkbox" and isinstance(val, list):
            val_display = ", ".join(f"`{v}`" for v in val)
        elif ftype == "date" and val:
            val_display = f"📅 **{val}**"
        elif ftype == "time" and val:
            val_display = f"🕒 **{val}**"
        elif ftype == "daterange" and isinstance(val, list) and len(val) >= 2:
            val_display = f"📅 **{val[0]}** 至 **{val[1]}**"
        elif ftype == "timerange" and isinstance(val, list) and len(val) >= 2:
            val_display = f"⏰ **{val[0]}** 至 **{val[1]}**"
        elif ftype == "switch":
            val_display = "✔ 是 (开启)" if val else "✖ 否 (关闭)"
        elif ftype == "rate":
            stars = int(val) if str(val).isdigit() else 0
            val_display = "⭐" * stars + f" ({stars} 星评级)"
        elif ftype == "slider":
            val_display = f"📊 完成进度: **{val}%**"
        elif ftype == "phone":
            val_display = f"📱 **{val}**"
        elif ftype == "gender":
            val_display = f"⚥ **{val}**"
        elif ftype == "email":
            val_display = f"📧 **{val}**"
        elif ftype == "nps":
            val_display = f"📊 NPS 评分: **{val} 分**"
        elif ftype == "ranking" and isinstance(val, list):
            val_display = "<br>".join(f"{idx+1}. {item}" for idx, item in enumerate(val))
        elif ftype == "signature":
            val_display = f"✍️ [已手写电子签字确认]"
        elif ftype == "image_upload" and isinstance(val, list):
            chips = [f"📷 [{f.get('name', '图片凭证')}]({f.get('url', '#')})" for f in val]
            val_display = "<br>".join(chips) if chips else "无图片"
        elif ftype == "subform" and isinstance(val, list):
            sub_cols = field.get("columns", [])
            sub_rows = []
            for r_idx, row in enumerate(val):
                row_items = [f"{c.get('label', c.get('id'))}: {row.get(c.get('id'), '')}" for c in sub_cols]
                sub_rows.append(f"第{r_idx+1}项: " + "，".join(row_items))
            val_display = "<br>".join(sub_rows) if sub_rows else "（无明细条目）"
        elif ftype == "attachment" and isinstance(val, list):
            chips = [f"📎 [{f.get('name') or f.get('original_name') or '附件'}]({f.get('url', '#')})" for f in val]
            val_display = "<br>".join(chips) if chips else "无附件"
        elif ftype == "textarea":
            clean_text = str(val).replace("\n", "<br>").replace("|", "｜")
            val_display = clean_text
        elif ftype in ("divider", "alert"):
            continue
        else:
            val_display = str(val).replace("|", "｜")

        clean_label = str(label).replace("|", "｜")
        lines.append(f"| **{clean_label}** | {val_display} |")

    lines.append("")
    lines.append("---")
    lines.append("*（注：本文档由 EDMS 低代码表单引擎自动合成与可信固化，支持多级协同流转与存证归档。）*")
    
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
#  PUBLIC — all authenticated employees can view published templates
# ──────────────────────────────────────────────────────────────
@bp.get("")
@jwt_required()
def list_templates():
    """List all published templates (is_template=True, is_public=True)."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    templates = (
        Document.query
        .filter_by(is_template=True, is_public=True, deleted_at=None)
        .order_by(Document.updated_at.desc())
        .all()
    )
    items = []
    for t in templates:
        schema_obj = _safe_load_schema(t.template_schema)
        items.append({
            "id": t.id,
            "title": t.title,
            "description": t.template_description or "",
            "icon": t.template_icon or "Document",
            "created_at": t.created_at.isoformat() + "Z" if t.created_at else None,
            "updated_at": t.updated_at.isoformat() + "Z" if t.updated_at else None,
            "owner_name": t.owner.display_name() if t.owner else "System",
            "is_low_code": bool(schema_obj and schema_obj.get("fields")),
            "fields_count": len(schema_obj.get("fields", [])) if schema_obj else 0,
            "template_schema": schema_obj
        })
    return jsonify({"items": items})


@bp.get("/<int:tmpl_id>")
@jwt_required()
def get_template_detail(tmpl_id: int):
    """Get single template detail, schema, and current content."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    tmpl = db.session.get(Document, tmpl_id)
    if not tmpl or not tmpl.is_template or tmpl.deleted_at:
        return jsonify({"error": "Template not found"}), 404

    schema_obj = _safe_load_schema(tmpl.template_schema)
    cur_ver = tmpl.current_version
    content = cur_ver.content_json if cur_ver else DocumentVersion.default_content_json()

    return jsonify({
        "id": tmpl.id,
        "title": tmpl.title,
        "description": tmpl.template_description or "",
        "icon": tmpl.template_icon or "Document",
        "is_public": tmpl.is_public,
        "is_low_code": bool(schema_obj and schema_obj.get("fields")),
        "template_schema": schema_obj,
        "content_json": content,
        "owner_name": tmpl.owner.display_name() if tmpl.owner else "System",
        "owner_id": tmpl.owner_id
    })


@bp.post("/<int:tmpl_id>/create-from")
@jwt_required()
def clone_from_template(tmpl_id: int):
    """Create a new draft document from a published template."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    tmpl = db.session.get(Document, tmpl_id)
    if not tmpl or not tmpl.is_template or not tmpl.is_public:
        return jsonify({"error": "Template not found"}), 404

    today_str = datetime.utcnow().strftime("%Y%m%d")
    max_doc = db.session.query(func.max(Document.doc_number)).filter(
        Document.doc_number.like(f"{today_str}%")
    ).scalar()
    if max_doc:
        try:
            last_seq = int(max_doc[-3:])
            doc_number = f"{today_str}{str(last_seq + 1).zfill(3)}"
        except Exception:
            doc_number = f"{today_str}001"
    else:
        doc_number = f"{today_str}001"

    doc = Document(
        owner_id=user.id,
        title=f"New from {tmpl.title}",
        status="draft",
        doc_number=doc_number
    )
    db.session.add(doc)
    db.session.flush()

    tmpl_ver = tmpl.current_version
    content_json = tmpl_ver.content_json if tmpl_ver else DocumentVersion.default_content_json()

    ver = DocumentVersion(
        document_id=doc.id,
        version_no=1,
        content_json=content_json,
        created_by_id=user.id,
    )
    db.session.add(ver)
    db.session.flush()
    doc.current_version_id = ver.id

    if tmpl.page_settings_json:
        doc.page_settings_json = tmpl.page_settings_json

    db.session.commit()
    return jsonify({"id": doc.id, "title": doc.title, "doc_number": doc.doc_number}), 201


@bp.post("/<int:tmpl_id>/generate-from-form")
@jwt_required()
def generate_doc_from_form(tmpl_id: int):
    """Runtime: generate a structured document from low-code form submission and optionally start approval."""
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    tmpl = db.session.get(Document, tmpl_id)
    if not tmpl or not tmpl.is_template or tmpl.deleted_at:
        return jsonify({"error": "Template not found"}), 404

    data = request.get_json(silent=True) or {}
    form_data = data.get("form_data", {})
    custom_title = (data.get("title") or "").strip()
    submit_for_approval = bool(data.get("submit_for_approval", False))
    approvers = data.get("approvers") or []
    flow_type = (data.get("flow_type") or "sequential").lower()
    
    schema = _safe_load_schema(tmpl.template_schema)
    if not schema:
        # Fallback to cloning if no low-code schema
        return clone_from_template(tmpl_id)

    today_str = datetime.utcnow().strftime("%Y%m%d")
    max_doc = db.session.query(func.max(Document.doc_number)).filter(
        Document.doc_number.like(f"{today_str}%")
    ).scalar()
    if max_doc:
        try:
            last_seq = int(max_doc[-3:])
            doc_number = f"{today_str}{str(last_seq + 1).zfill(3)}"
        except Exception:
            doc_number = f"{today_str}001"
    else:
        doc_number = f"{today_str}001"

    doc_title = custom_title or f"{tmpl.title} - {user.display_name()} ({datetime.utcnow().strftime('%m/%d')})"

    user_name = user.display_name()
    dept_name = user.department.name if user.department else "未分配部门"

    # Auto-generate structured Markdown content from schema & form data
    doc_markdown = _generate_doc_markdown_from_form(
        title=doc_title,
        form_data=form_data,
        schema=schema,
        user_name=user_name,
        dept_name=dept_name,
        doc_number=doc_number
    )

    doc = Document(
        owner_id=user.id,
        title=doc_title,
        status="draft",
        doc_number=doc_number,
        template_icon=tmpl.template_icon or "Document",
        template_schema=json.dumps(schema) if isinstance(schema, dict) else tmpl.template_schema,
        doc_type="low_code_form"
    )
    db.session.add(doc)
    db.session.flush()

    ver = DocumentVersion(
        document_id=doc.id,
        version_no=1,
        content_json=json.dumps({
            "form_data": form_data,
            "schema": schema,
            "markdown": doc_markdown
        }),
        created_by_id=user.id
    )
    db.session.add(ver)
    db.session.flush()
    doc.current_version_id = ver.id

    flow_id = None
    # 💡 核心业务流转：如果员工选择“提交并流转审批”，立即自动启动审批流！
    if submit_for_approval and approvers:
        from app.services.approval_service import start_flow
        from app.models.notification import Notification
        
        valid_approver_ids = [int(x) for x in approvers if int(x) != user.id]
        if valid_approver_ids:
            flow = start_flow(doc, flow_type, valid_approver_ids)
            flow_id = flow.id
            
            # 发送审批通知
            for uid in valid_approver_ids:
                n = Notification()
                n.user_id = uid
                n.type = "审批"
                n.title = f"待审批: {doc.title}"
                n.content = f"员工 {user_name} 提交了业务单据 '{doc.title}'，请您审核。"
                n.related_doc_id = doc.id
                n.link_url = f"/inbox"
                db.session.add(n)

    db.session.commit()
    return jsonify({
        "id": doc.id,
        "title": doc.title,
        "doc_number": doc.doc_number,
        "status": doc.status,
        "flow_id": flow_id,
        "message": "Document generated and routed successfully"
    }), 201


# ──────────────────────────────────────────────────────────────
#  ADMIN — full management & Low-Code Design of templates
# ──────────────────────────────────────────────────────────────
@bp.get("/admin")
@jwt_required()
def admin_list_templates():
    """Admin/Manager: list all templates for management."""
    user = current_user()
    if not _can_manage_templates(user):
        return jsonify({"error": "Forbidden"}), 403

    templates = Document.query.filter_by(is_template=True, deleted_at=None).order_by(Document.updated_at.desc()).all()
    items = []
    for t in templates:
        schema_obj = _safe_load_schema(t.template_schema)
        items.append({
            "id": t.id,
            "title": t.title,
            "description": t.template_description or "",
            "icon": t.template_icon or "Document",
            "is_public": t.is_public,
            "created_at": t.created_at.isoformat() + "Z" if t.created_at else None,
            "updated_at": t.updated_at.isoformat() + "Z" if t.updated_at else None,
            "owner_name": t.owner.display_name() if t.owner else "System",
            "owner_id": t.owner_id,
            "is_low_code": bool(schema_obj and schema_obj.get("fields")),
            "fields_count": len(schema_obj.get("fields", [])) if schema_obj else 0,
            "template_schema": schema_obj
        })
    return jsonify({"items": items})


@bp.post("/admin")
@jwt_required()
def admin_create_template():
    """Admin/Manager: create a new template (rich text or low code)."""
    user = current_user()
    if not _can_manage_templates(user):
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled Template").strip()[:512]
    description = (data.get("description") or "").strip()[:512]
    is_public = bool(data.get("is_public", False))
    schema_data = data.get("template_schema")
    if schema_data and isinstance(schema_data, (dict, list)):
        schema_str = json.dumps(schema_data, ensure_ascii=False)
    elif schema_data:
        schema_str = str(schema_data)
    else:
        schema_str = None

    today_str = datetime.utcnow().strftime("%Y%m%d")
    max_doc = db.session.query(func.max(Document.doc_number)).filter(
        Document.doc_number.like(f"{today_str}%")
    ).scalar()
    if max_doc:
        try:
            last_seq = int(max_doc[-3:])
            doc_number = f"{today_str}{str(last_seq + 1).zfill(3)}"
        except Exception:
            doc_number = f"{today_str}001"
    else:
        doc_number = f"{today_str}001"

    tmpl = Document(
        owner_id=user.id,
        title=title,
        template_description=description,
        template_icon=data.get("icon", "Document"),
        status="draft",
        is_template=True,
        is_public=is_public,
        doc_number=doc_number,
        template_schema=schema_str
    )
    db.session.add(tmpl)
    db.session.flush()

    ver = DocumentVersion(
        document_id=tmpl.id,
        version_no=1,
        content_json=DocumentVersion.default_content_json(),
        created_by_id=user.id,
    )
    db.session.add(ver)
    db.session.flush()
    tmpl.current_version_id = ver.id

    db.session.commit()
    return jsonify({
        "id": tmpl.id,
        "title": tmpl.title,
        "description": tmpl.template_description or "",
        "icon": tmpl.template_icon or "Document",
        "is_public": tmpl.is_public,
        "template_schema": _safe_load_schema(tmpl.template_schema),
        "is_low_code": bool(tmpl.template_schema)
    }), 201


@bp.patch("/admin/<int:tmpl_id>")
@bp.put("/admin/<int:tmpl_id>")
@jwt_required()
def admin_update_template(tmpl_id: int):
    """Admin/Manager: update template metadata and low-code schema."""
    user = current_user()
    if not _can_manage_templates(user):
        return jsonify({"error": "Forbidden"}), 403

    tmpl = db.session.get(Document, tmpl_id)
    if not tmpl or not tmpl.is_template:
        return jsonify({"error": "Template not found"}), 404
        
    if not _is_super_admin(user) and tmpl.owner_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}
    if "title" in data:
        tmpl.title = (data["title"] or "Untitled Template").strip()[:512]
    if "description" in data:
        tmpl.template_description = (data["description"] or "").strip()[:512]
    if "icon" in data:
        tmpl.template_icon = (data["icon"] or "Document").strip()[:64]
    if "is_public" in data:
        tmpl.is_public = bool(data["is_public"])
    if "template_schema" in data:
        schema_data = data["template_schema"]
        if schema_data and isinstance(schema_data, (dict, list)):
            tmpl.template_schema = json.dumps(schema_data, ensure_ascii=False)
        elif schema_data:
            tmpl.template_schema = str(schema_data)
        else:
            tmpl.template_schema = None

    tmpl.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        "id": tmpl.id,
        "title": tmpl.title,
        "description": tmpl.template_description or "",
        "icon": tmpl.template_icon or "Document",
        "is_public": tmpl.is_public,
        "template_schema": _safe_load_schema(tmpl.template_schema),
        "is_low_code": bool(tmpl.template_schema)
    })


@bp.delete("/admin/<int:tmpl_id>")
@jwt_required()
def admin_delete_template(tmpl_id: int):
    """Admin/Manager: soft-delete a template."""
    user = current_user()
    if not _can_manage_templates(user):
        return jsonify({"error": "Forbidden"}), 403

    tmpl = db.session.get(Document, tmpl_id)
    if not tmpl or not tmpl.is_template:
        return jsonify({"error": "Template not found"}), 404
        
    if not _is_super_admin(user) and tmpl.owner_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    tmpl.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/admin/<int:tmpl_id>/publish")
@jwt_required()
def admin_publish_template(tmpl_id: int):
    """Admin/Manager: publish a template."""
    user = current_user()
    if not _can_manage_templates(user):
        return jsonify({"error": "Forbidden"}), 403

    tmpl = db.session.get(Document, tmpl_id)
    if not tmpl or not tmpl.is_template:
        return jsonify({"error": "Template not found"}), 404
        
    if not _is_super_admin(user) and tmpl.owner_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    tmpl.is_public = True
    tmpl.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"id": tmpl.id, "is_public": True})


@bp.post("/admin/<int:tmpl_id>/unpublish")
@jwt_required()
def admin_unpublish_template(tmpl_id: int):
    """Admin/Manager: unpublish a template."""
    user = current_user()
    if not _can_manage_templates(user):
        return jsonify({"error": "Forbidden"}), 403

    tmpl = db.session.get(Document, tmpl_id)
    if not tmpl or not tmpl.is_template:
        return jsonify({"error": "Template not found"}), 404
        
    if not _is_super_admin(user) and tmpl.owner_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    tmpl.is_public = False
    tmpl.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"id": tmpl.id, "is_public": False})


# ──────────────────────────────────────────────────────────────
#  AI ASSISTANT — Generate Low-Code Form Schema from Prompt
# ──────────────────────────────────────────────────────────────
@bp.post("/ai-generate-schema")
@jwt_required()
def ai_generate_template_schema():
    """Use AI to automatically build a low-code form schema from a prompt."""
    user = current_user()
    if not _can_manage_templates(user):
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    system_prompt = (
        "你是一个顶级的企业级低代码表单与文档模板架构专家。"
        "请根据用户的需求，生成结构化表单字段配置（JSON 格式）。\n"
        "要求输出严格的 JSON 对象，包含以下字段：\n"
        "1. title: 模板标题 (字符串)\n"
        "2. description: 模板业务说明 (字符串)\n"
        "3. icon: Element Plus 图标名 (如 Document, Tickets, Money, Calendar, Stamp, Files)\n"
        "4. fields: 字段列表数组，每个字段对象包含：\n"
        "   - id: 字段英文字段名 (如 f_title, f_amount, f_date, f_reason, f_dept)\n"
        "   - label: 字段中文标签 (如 '采购物品名称', '采购数量', '预算金额 (元)', '申请日期')\n"
        "   - type: 控件类型 (可选: 'text', 'textarea', 'number' (纯数字/数量/工时/天数), 'amount' (财务金额/预算), 'date', 'daterange', 'time', 'timerange', 'select', 'radio', 'checkbox', 'switch', 'rate', 'slider', 'dept_select', 'user_select', 'attachment', 'subform')\n"
        "   - placeholder: 输入提示\n"
        "   - required: 是否必填 (true/false)\n"
        "   - defaultValue: 默认值\n"
        "   - options: 下拉/单选选项数组 (若 type 为 select/radio/checkbox)\n"
        "   - unit: 数量单位后缀 (如 '个', '件', '天', '小时', '台', '元')\n"
        "   - min / max / step / precision: 数值上下限/步长/小数保留位数 (若 type 为 number 或 amount)\n"
        "请只返回合法的 JSON 对象，不要附加任何 markdown 标记或解释文字。"
    )

    try:
        client = AIService.get_client("deepseek")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请为我设计如下业务表单模板：{prompt}"}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        raw_text = response.choices[0].message.content or "{}"
        
        # Clean markdown codeblocks if any
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            schema_json = json.loads(json_match.group(0))
        else:
            schema_json = json.loads(raw_text)

        return jsonify({"schema": schema_json})

    except Exception as e:
        # Fallback intelligent rule-based schema generator if AI call is not reachable
        fallback_title = prompt.split("，")[0].split("。")[0][:30] or "业务审批表单"
        fallback_schema = {
            "title": fallback_title,
            "description": f"用于办理 {prompt} 的标准化低代码业务申请表单",
            "icon": "Tickets",
            "fields": [
                {
                    "id": "f_title",
                    "label": "申请事项 / 项目名称",
                    "type": "text",
                    "placeholder": "请输入事项简述",
                    "required": True,
                    "defaultValue": ""
                },
                {
                    "id": "f_dept",
                    "label": "申请部门",
                    "type": "dept_select",
                    "placeholder": "选择所在部门",
                    "required": True
                },
                {
                    "id": "f_date",
                    "label": "期望交付 / 生效日期",
                    "type": "date",
                    "placeholder": "选择日期",
                    "required": True
                },
                {
                    "id": "f_priority",
                    "label": "紧急程度",
                    "type": "select",
                    "options": ["普通", "加急", "特急"],
                    "defaultValue": "普通",
                    "required": True
                },
                {
                    "id": "f_amount",
                    "label": "预估金额 / 预算 (元)",
                    "type": "number",
                    "placeholder": "0.00",
                    "min": 0,
                    "step": 100,
                    "required": False
                },
                {
                    "id": "f_reason",
                    "label": "申请事由与详细说明",
                    "type": "textarea",
                    "placeholder": "请详细阐述申请背景、需求及目标...",
                    "required": True
                }
            ]
        }
        return jsonify({"schema": fallback_schema, "is_fallback": True})
