from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required
from app.services.ai_service import AIService
from app.utils.auth import current_user
from app.services.document_access import user_can_view_document
import json
import os
from datetime import datetime

bp = Blueprint("ai", __name__)

@bp.post("/chat")
@jwt_required()
def ai_chat():
    try:
        data = request.get_json(silent=True) or {}
        messages = data.get("messages", [])
        context_url = data.get("context_url", "")
        doc_context = data.get("doc_context", "")

        ai_model = data.get("ai_model", "deepseek")
        user = current_user()
        user_info = {
            "id": user.id if user else 0,
            "login_name": user.login_name if user else "guest"
        }
        
        from app.extensions import db
        db.session.remove()
        
        return Response(
            stream_with_context(AIService.stream_chat(
                messages, 
                user_context=context_url, 
                doc_context=doc_context, 
                current_user=user_info,
                ai_model=ai_model
            )),
            mimetype="text/event-stream"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
def get_document_text(doc):
    ver = doc.current_version
    if not ver:
        return doc.title
        
    text_content = ""
    if doc.doc_type == "pdf":
        # 1. Try to load from content_json first
        if ver.content_json:
            try:
                cj = json.loads(ver.content_json) if isinstance(ver.content_json, str) else ver.content_json
                from app.utils.text import extract_text_from_tiptap
                text_content = extract_text_from_tiptap(cj)
            except Exception:
                pass
                
        # 2. Try to parse PDF on-demand if content_json is empty and file_path exists
        if not text_content and ver.file_path:
            import os
            from flask import current_app
            storage_base = os.environ.get("STORAGE_PATH", current_app.root_path)
            rel_path = ver.file_path.lstrip('/')
            abs_path = os.path.join(storage_base, rel_path)
            if os.path.exists(abs_path):
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(abs_path)
                    text_content = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                except Exception as e:
                    print(f"Error parsing PDF on demand: {e}")
    elif doc.doc_type == "spreadsheet":
        if ver.content_json:
            try:
                sj = json.loads(ver.content_json) if isinstance(ver.content_json, str) else ver.content_json
                sheets = sj.get("sheets", [])
                parts = []
                for s in sheets:
                    s_name = s.get("name", "Sheet")
                    cells = s.get("data", {})
                    sample_values = []
                    for k, cell_obj in list(cells.items())[:30]:
                        if isinstance(cell_obj, dict):
                            val = cell_obj.get("v") or cell_obj.get("m") or ""
                        else:
                            val = str(cell_obj)
                        if val:
                            sample_values.append(str(val))
                    parts.append(f"工作表: {s_name}\n数据样本: {', '.join(sample_values[:20])}")
                text_content = "\n\n".join(parts)
            except Exception:
                pass
    else:
        # Rich text document
        if ver.content_json:
            try:
                cj = json.loads(ver.content_json) if isinstance(ver.content_json, str) else ver.content_json
                from app.utils.text import extract_text_from_tiptap
                text_content = extract_text_from_tiptap(cj)
            except Exception:
                pass
                
    return text_content if text_content else doc.title

@bp.post("/generate-title")
@jwt_required()
def ai_generate_title():
    user = current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    doc_id = data.get("doc_id")
    doc_type = data.get("doc_type", "rich_text")
    ai_model = data.get("ai_model", "deepseek")
    lang = data.get("lang", "zh")

    if (not content or len(content) < 5) and doc_id:
        from app.models.document import Document
        from app.services.document_access import user_can_view_document
        doc = Document.get_by_id_or_number(doc_id)
        if doc and user_can_view_document(user, doc):
            content = get_document_text(doc)
            doc_type = doc.doc_type

    if not content or len(content.strip()) < 5:
        return jsonify({
            "success": False,
            "title": "",
            "error": "文档内容为空或过少，无法识别生成有效标题"
        }), 400

    result = AIService.generate_document_title(content, doc_type=doc_type, ai_model=ai_model, lang=lang)
    if not result.get("success"):
        return jsonify(result), 400
        
    return jsonify(result)

@bp.route("/generate", methods=["POST"])
@jwt_required()
def ai_generate():
    data = request.get_json() or {}
    doc_id = data.get("doc_id")
    action = data.get("action", "")
    lang = data.get("lang", "zh")
    ai_model = data.get("ai_model", "deepseek")
    
    prompt = ""
    if doc_id:
        from app.models.document import Document
        from app.services.document_access import user_can_view_document
        
        user = current_user()
        doc = Document.get_by_id_or_number(doc_id)
        if not doc or not user_can_view_document(user, doc):
            return jsonify({"error": "Document not found or access denied"}), 404
            
        prompt = get_document_text(doc)
    else:
        prompt = data.get("prompt", "")
        
    if not prompt:
        return jsonify({"error": "No prompt or document content provided"}), 400
        
    # Limit prompt length to avoid token limit issues
    prompt = prompt[:5000]
    
    from app.extensions import db
    db.session.remove()
    
    return Response(
        stream_with_context(AIService.stream_generate(prompt, action, lang, ai_model=ai_model)),
        mimetype="text/event-stream"
    )

@bp.post("/import-image")
@jwt_required()
def import_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    
    result = AIService.ocr_and_format(file)
    
    # Create document in DB (Simplified for now)
    from app.models import Document, DocumentVersion
    from app.extensions import db
    user = current_user()
    
    try:
        from datetime import datetime
        today_str = datetime.now().strftime("%Y%m%d")
        # Logic to generate doc number if needed, but let's keep it simple
        doc_number = f"IMG{today_str}{random_str(3)}" 
        
        doc = Document()
        doc.owner_id = user.id
        doc.title = result["title"]
        doc.status = "draft"
        doc.doc_number = doc_number
        db.session.add(doc)
        db.session.flush()
        
        ver = DocumentVersion()
        ver.document_id = doc.id
        ver.version_no = 1
        ver.content_json = json.dumps({"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": result["content"]}]}]}) # Simplified
        ver.created_by_id = user.id
        # Actually it's better to store as Markdown if the system supports it, 
        # but the current system seems to use Tiptap JSON. 
        # For simplicity, we'll return the ID and content preview.
        
        db.session.add(ver)
        doc.current_version = ver # 💡 Use object relationship to ensure ID is handled correctly
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "data": {
                "document_id": doc.id,
                "title": doc.title,
                "content_preview": result["content"][:200]
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def _add_wav_header(pcm_data):
    """Add a 44-byte WAV header to raw PCM data (16k, 16bit, mono)."""
    header = bytearray()
    header.extend(b'RIFF')
    header.extend((len(pcm_data) + 36).to_bytes(4, 'little'))
    header.extend(b'WAVEfmt ')
    header.extend((16).to_bytes(4, 'little'))
    header.extend((1).to_bytes(2, 'little'))
    header.extend((1).to_bytes(2, 'little'))
    header.extend((16000).to_bytes(4, 'little'))
    header.extend((32000).to_bytes(4, 'little'))
    header.extend((2).to_bytes(2, 'little'))
    header.extend((16).to_bytes(2, 'little'))
    header.extend(b'data')
    header.extend(len(pcm_data).to_bytes(4, 'little'))
    return header + pcm_data

@bp.post("/meeting-summary")
@jwt_required()
def meeting_summary():
    if "audio" not in request.files:
        return jsonify({"error": "No audio part"}), 400
    file = request.files["audio"]
    
    try:
        # Debug: Save audio file locally
        debug_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "debug_audio"))
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_filename = f"meeting_{timestamp}_{file.filename}"
        debug_path = os.path.join(debug_dir, debug_filename)
        
        # Save a copy (handle both PCM and WebM for now)
        pcm_data = file.read()
        if len(pcm_data) > 0:
            with open(debug_path, "wb") as f:
                # If it looks like PCM (no header), add one for playback
                if pcm_data[:4] != b'RIFF':
                    f.write(_add_wav_header(pcm_data))
                else:
                    f.write(pcm_data)
        
        file.seek(0)
        
        # Use real transcription
        text = AIService.transcribe_audio(file)
        
        # Generate a summary using AI after transcription
        summary_markdown = "### 语音转写结果\n" + text
        if len(text) > 20:
             # If text is long enough, try to generate a real summary
             # For now, just return the text as it's better than a mock
             pass

        return jsonify({
            "code": 200,
            "data": {
                "original_text": text,
                "summary_markdown": summary_markdown
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/transcribe")
@jwt_required()
def ai_transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio part"}), 400
    file = request.files["audio"]
    
    try:
        # Debug: Save audio file locally to check if recording is working
        debug_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "debug_audio"))
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_filename = f"debug_{timestamp}_{file.filename}"
        debug_path = os.path.join(debug_dir, debug_filename)
        
        # Save a copy with WAV header
        pcm_data = file.read()
        wav_data = _add_wav_header(pcm_data)
        with open(debug_path, "wb") as f:
            f.write(wav_data)
        
        print(f"[DEBUG] Audio saved to: {debug_path}")
        
        # Reset file pointer for transcription service
        file.seek(0)

        text = AIService.transcribe_audio(file)
        return jsonify({
            "code": 200,
            "text": text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.get("/history")
@jwt_required()
def get_ai_history():
    from app.services.ai_history_store import ai_history_store
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    doc_id = request.args.get("document_id", type=int)
    
    # Only admin can see all, users see their own
    user = current_user()
    user_id = None if user.is_super_admin else user.id
    
    history = ai_history_store.get_all(page=page, per_page=per_page, document_id=doc_id, user_id=user_id)
    return jsonify({
        "code": 200,
        "data": history
    })

@bp.delete("/history/<int:history_id>")
@jwt_required()
def delete_ai_history(history_id):
    from app.services.ai_history_store import ai_history_store
    success = ai_history_store.delete(history_id)
    if success:
        return jsonify({"code": 200, "message": "Success"})
    return jsonify({"error": "Not found"}), 404

@bp.post("/cross-qa")
@jwt_required()
def cross_document_qa():
    data = request.get_json(silent=True) or {}
    doc_ids = data.get("doc_ids", [])
    query = data.get("query", "")
    ai_model = data.get("ai_model", "deepseek")
    
    if not doc_ids or not query:
        return jsonify({"error": "Missing doc_ids or query"}), 400

    # [SECURITY - VULN-02 FIX] Verify the current user has view access to every requested document.
    # Previously there was no permission check, allowing any authenticated user to read
    # the content of arbitrary documents by enumerating doc_ids (IDOR vulnerability).
    user = current_user()
    from app.models import Document
    from app.extensions import db as _db
    authorized_doc_ids = []
    for did in doc_ids:
        doc = _db.session.get(Document, did)
        if doc and user_can_view_document(user, doc):
            authorized_doc_ids.append(did)
        # Silently skip documents user cannot view (don't leak existence via error)
    
    if not authorized_doc_ids:
        return jsonify({"error": "No accessible documents found in the provided list."}), 403

    from app.services.vector_store import search_documents
    
    # 1. 尝试使用向量搜索 (Semantic Search) + 增大 Top-K 确保历史数据覆盖
    contexts = search_documents(query, doc_ids=authorized_doc_ids, limit=20)
    
    # 2. 兜底策略：如果向量数据库没有返回结果，则直接从 MySQL 提取文档原文
    if not contexts:
        print(f"[AI QA] 向量搜索未返回结果 (Docs: {authorized_doc_ids})，正在尝试从数据库直接提取内容...")
        from app.models import Document
        from app.utils.text import extract_text_from_tiptap
        from app.extensions import db
        
        for did in authorized_doc_ids:
            doc = db.session.get(Document, did)
            if doc and doc.current_version:
                text = ""
                try:
                    # 尝试解析富文本内容
                    cj = json.loads(doc.current_version.content_json)
                    text = extract_text_from_tiptap(cj)
                except:
                    text = doc.title
                
                if text:
                    contexts.append({
                        "doc_id": doc.id,
                        "title": doc.title,
                        "text": text[:8000] # 增大兜底提取长度，确保历史深度
                    })
    
    context_list = []
    for i, c in enumerate(contexts, 1):
        context_list.append(f"[片段{i}][文档ID: {c.get('doc_id')}][来源：《{c.get('title')}》]：{c.get('text')}")
    context_data = "\n".join(context_list)
    
    system_prompt_override = f"""# Role
你是企业级电子文档管理系统（EDMS）的专属知识库智能助手。你的核心任务是根据系统提供的【企业内部文档检索片段】（Context），准确、专业地回答用户的提问，并主动提供参考文档的跳转链接。

# Context (检索上下文)
以下是系统从向量数据库中为你检索到的相关内部文档片段：
<context>
{context_data}
</context>
注：{context_data} 包含多个片段，每个片段都会标明 [来源文档标题] 和 [DocID]。

# Rules (核心规则)
1. **严格基于事实**：你必须且只能基于上述 <context> 中提供的信息回答问题，绝不允许使用通用先验知识进行编造或猜测（严禁幻觉）。
2. **信息缺失时拒绝**：如果 <context> 中没有任何能回答用户问题的信息，请直接回复：“抱歉，在当前的企业文档库中未检索到关于此问题的相关信息。”
3. **结构化输出**：回答需条理清晰，使用 Markdown 格式（如无序列表、加粗）突出关键数据和结论。
4. **强制附加跳转链接（最高优先级）**：当你的回答引用了上述 <context> 中的文档时，必须在回答的最末尾，严格使用以下 Markdown 格式生成文档入口：
   [点击查看原文档：《{{文档标题}}》](/editor/{{DocID}})
   *警告：必须保证 {{文档标题}} 和 {{DocID}} 与 <context> 中提供的信息完全一致，且链接路径前缀不得更改。*"""

    messages = [
        {"role": "user", "content": f"# 用户问题 (User Query)\n{query}"}
    ]
    user = current_user()
    user_info = {
        "id": user.id if user else 0,
        "login_name": user.login_name if user else "guest"
    }
    
    from app.extensions import db
    db.session.remove()
    
    return Response(
        stream_with_context(AIService.stream_chat(
            messages, 
            user_context="多文档联合分析", 
            doc_context="", 
            current_user=user_info,
            ai_model=ai_model,
            system_prompt_override=system_prompt_override
        )),
        mimetype="text/event-stream"
    )

@bp.post("/check-logic")
@jwt_required()
def check_logic():
    data = request.get_json(silent=True) or {}
    doc_id = data.get("doc_id")
    ai_model = data.get("ai_model", "deepseek")
    lang = data.get("lang", "zh")
    
    if not doc_id:
        return jsonify({"error": "Missing doc_id"}), 400
        
    from app.models import Document
    from app.extensions import db
    doc = Document.get_by_id_or_number(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    # [SECURITY - VULN-02 FIX] Verify the current user has view access to this document.
    # Previously any authenticated user could check the logic of any document by ID (IDOR).
    user = current_user()
    if not user_can_view_document(user, doc):
        return jsonify({"error": "Document not found"}), 404  # Use 404 to avoid leaking document existence
        
    text_content = get_document_text(doc)
        
    # IMPORTANT: Release connection back to pool before slow network IO!
    db.session.remove()
        
    result = AIService.check_logic(text_content, ai_model=ai_model, lang=lang)
    return jsonify({"code": 200, "data": result})

@bp.post("/spreadsheet/formula")
@jwt_required()
def ai_spreadsheet_formula():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    cell_address = data.get("cell_address", "A1")
    range_context = data.get("range_context", "")
    sheet_sample = data.get("sheet_sample", "")
    ai_model = data.get("ai_model", "deepseek")
    lang = data.get("lang", "zh")

    if not query:
        return jsonify({"error": "Missing query description"}), 400

    result = AIService.generate_spreadsheet_formula(
        query=query,
        cell_address=cell_address,
        range_context=range_context,
        sheet_sample=sheet_sample,
        ai_model=ai_model,
        lang=lang
    )
    return jsonify({"code": 200, "data": result})

@bp.post("/spreadsheet/generate-table")
@jwt_required()
def ai_spreadsheet_generate_table():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    row_count = int(data.get("row_count", 8))
    col_count = int(data.get("col_count", 5))
    ai_model = data.get("ai_model", "deepseek")
    lang = data.get("lang", "zh")

    if not prompt:
        return jsonify({"error": "Missing table prompt"}), 400

    result = AIService.generate_spreadsheet_table(
        prompt=prompt,
        row_count=row_count,
        col_count=col_count,
        ai_model=ai_model,
        lang=lang
    )
    return jsonify({"code": 200, "data": result})

@bp.post("/spreadsheet/insights")
@jwt_required()
def ai_spreadsheet_insights():
    data = request.get_json(silent=True) or {}
    sheet_name = data.get("sheet_name", "Sheet1")
    headers = data.get("headers", [])
    rows_sample = data.get("rows_sample", [])
    total_rows = int(data.get("total_rows", 0))
    ai_model = data.get("ai_model", "deepseek")
    lang = data.get("lang", "zh")

    result = AIService.analyze_spreadsheet_insights(
        sheet_name=sheet_name,
        headers=headers,
        rows_sample=rows_sample,
        total_rows=total_rows,
        ai_model=ai_model,
        lang=lang
    )
    return jsonify({"code": 200, "data": result})

@bp.post("/spreadsheet/process-range")
@jwt_required()
def ai_spreadsheet_process_range():
    data = request.get_json(silent=True) or {}
    action = data.get("action", "clean")
    range_data = data.get("range_data", [])
    prompt = data.get("prompt", "")
    target_lang = data.get("target_lang", "en")
    ai_model = data.get("ai_model", "deepseek")

    if not range_data:
        return jsonify({"error": "Missing range_data matrix"}), 400

    result = AIService.process_spreadsheet_range(
        action=action,
        range_data=range_data,
        prompt=prompt,
        target_lang=target_lang,
        ai_model=ai_model
    )
    return jsonify({"code": 200, "data": result})

def random_str(length):
    import random
    import string
    return "".join(random.choices(string.digits, k=length))

