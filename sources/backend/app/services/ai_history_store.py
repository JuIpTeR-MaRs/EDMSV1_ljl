"""AI对话历史持久化存储服务"""
import json
import os
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import os
from app.extensions import db # Add any necessary extension imports if needed but we just need os for path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
if not os.path.exists(INSTANCE_DIR):
    os.makedirs(INSTANCE_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(INSTANCE_DIR, "ai_history.json")

class AIHistoryStore:
    """线程安全的AI对话历史存储（带有5天持久化和清理机制）"""
    
    def __init__(self):
        self._store: List[Dict] = []
        self._lock = threading.Lock()
        self._next_id = 1
        self._load_from_disk()
    
    def _load_from_disk(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._store = data.get("store", [])
                    # Clean up 'ai_model' key from existing records to ensure it's deleted from the DB/file
                    for conv in self._store:
                        conv.pop("ai_model", None)
                    self._next_id = data.get("next_id", 1)
                self._clean_old_records()
            except Exception as e:
                print(f"[AI HISTORY] Failed to load history: {e}")
                self._store = []
                self._next_id = 1

    def _save_to_disk(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "store": self._store,
                    "next_id": self._next_id
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AI HISTORY] Failed to save history: {e}")

    def _clean_old_records(self):
        """清理超过5天的记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=5)
        original_count = len(self._store)
        
        valid_records = []
        for conv in self._store:
            try:
                # 兼容旧版本可能没有 timezone 信息的 isoformat
                created_at = datetime.fromisoformat(conv["created_at"].replace('Z', '+00:00'))
                if created_at.tzinfo:
                    created_at = created_at.replace(tzinfo=None) # 转为 naive 方便对比
                if created_at > cutoff_date:
                    valid_records.append(conv)
            except Exception:
                # 如果解析出错，保留该记录
                valid_records.append(conv)
                
        self._store = valid_records
        if len(self._store) < original_count:
            print(f"[AI HISTORY] Cleaned {original_count - len(self._store)} old records (>5 days)")

    def add_conversation(self, user_id: int, user_name: str, question: str, 
                        answer: str, document_id: Optional[int] = None,
                        document_title: Optional[str] = None,
                        context_url: Optional[str] = None,
                        action_type: str = "chat",
                        ai_model: Optional[str] = None,
                        tokens_used: Optional[int] = None) -> Dict:
        """添加对话记录"""
        with self._lock:
            self._clean_old_records()
            conversation = {
                "id": self._next_id,
                "user_id": user_id,
                "user_name": user_name,
                "document_id": document_id,
                "document_title": document_title,
                "question": question,
                "answer": answer,
                "context_url": context_url,
                "action_type": action_type,
                "created_at": datetime.utcnow().isoformat(),
                "tokens_used": tokens_used,
            }
            self._store.append(conversation)
            self._next_id += 1
            
            self._save_to_disk()
            
            # 控制台打印详细信息
            print("\n" + "="*80)
            print(f"[AI HISTORY] New Conversation #{conversation['id']}")
            print("="*80)
            print(f"User: {user_name} (ID: {user_id})")
            print(f"Document: {document_title or 'N/A'} (ID: {document_id or 'N/A'})")
            print(f"Time: {conversation['created_at']}")
            print(f"Type: {action_type}")
            print("-"*80)
            print(f"Question:\n{question[:500]}{'...' if len(question) > 500 else ''}")
            print("-"*80)
            print(f"Answer:\n{answer[:500]}{'...' if len(answer) > 500 else ''}")
            print("="*80 + "\n")
            
            return conversation
    
    def get_all(self, page: int = 1, per_page: int = 20, 
                document_id: Optional[int] = None,
                user_id: Optional[int] = None) -> Dict:
        """获取分页历史记录"""
        with self._lock:
            self._clean_old_records()
            filtered = self._store.copy()
            
            # 过滤条件
            if document_id:
                filtered = [c for c in filtered if c.get("document_id") == document_id]
            if user_id:
                filtered = [c for c in filtered if c.get("user_id") == user_id]
            
            # 按时间倒序
            filtered.sort(key=lambda x: x["created_at"], reverse=True)
            
            # 分页
            total = len(filtered)
            start = (page - 1) * per_page
            end = start + per_page
            items = filtered[start:end]
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page if per_page > 0 else 0
            }
    
    def delete(self, conv_id: int) -> bool:
        """删除单条记录"""
        with self._lock:
            for i, conv in enumerate(self._store):
                if conv["id"] == conv_id:
                    self._store.pop(i)
                    self._save_to_disk()
                    print(f"[AI HISTORY] Deleted conversation #{conv_id}")
                    return True
            return False
    
    def clear(self, document_id: Optional[int] = None, user_id: Optional[int] = None) -> int:
        """清空历史记录"""
        with self._lock:
            if document_id:
                original_count = len(self._store)
                self._store = [c for c in self._store if c.get("document_id") != document_id]
                deleted = original_count - len(self._store)
            elif user_id:
                original_count = len(self._store)
                self._store = [c for c in self._store if c.get("user_id") != user_id]
                deleted = original_count - len(self._store)
            else:
                deleted = len(self._store)
                self._store.clear()
            
            self._save_to_disk()
            print(f"[AI HISTORY] Cleared {deleted} conversations")
            return deleted
    
    def get_count(self) -> int:
        """获取总记录数"""
        with self._lock:
            self._clean_old_records()
            return len(self._store)

    def get_summary_stats(self) -> Dict:
        """获取摘要统计信息用于仪表盘"""
        with self._lock:
            self._clean_old_records()
            total = len(self._store)
            return {
                "total_interactions": total,
                "model_distribution": []
            }


# 全局单例
ai_history_store = AIHistoryStore()
