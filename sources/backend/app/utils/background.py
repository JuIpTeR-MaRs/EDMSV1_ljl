import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

# Global thread pool for background tasks
# We use a ThreadPoolExecutor to run tasks in the background without blocking the main thread.
executor = ThreadPoolExecutor(max_workers=4)

# Global task state storage
# task_id -> { "name": str, "status": str, "progress": int, "message": str, "result": Any, "error": str }
_tasks = {}
_tasks_lock = threading.Lock()

def run_in_background(func, *args, **kwargs):
    """
    Submits a function to be executed in the background thread pool.
    """
    executor.submit(func, *args, **kwargs)

def create_task(name: str) -> str:
    """
    Creates a new task in the registry and returns its unique ID.
    """
    task_id = str(uuid.uuid4())
    with _tasks_lock:
        _tasks[task_id] = {
            "name": name,
            "status": "pending",
            "progress": 0,
            "message": "Task created",
            "result": None,
            "error": None
        }
    return task_id

def update_task(task_id: str, progress: int, status: str = None, message: str = None, result: any = None, error: str = None):
    """
    Updates the progress, status, and messages of a background task, then emits updates via SocketIO.
    """
    with _tasks_lock:
        if task_id not in _tasks:
            return
        task = _tasks[task_id]
        task["progress"] = progress
        if status:
            task["status"] = status
        if message:
            task["message"] = message
        if result is not None:
            task["result"] = result
        if error is not None:
            task["error"] = error

        # Prepare payload for Socket.IO
        payload = {
            "task_id": task_id,
            "name": task["name"],
            "status": task["status"],
            "progress": task["progress"],
            "message": task["message"],
            "result": task["result"],
            "error": task["error"]
        }

    # Emit Socket.IO progress update outside the lock
    try:
        from app.extensions import socketio
        socketio.emit("task_progress", payload)
    except Exception as e:
        print(f"[Background] Failed to emit task progress via SocketIO: {e}")

def get_task_status(task_id: str) -> dict:
    """
    Retrieves the current state of a task by ID.
    """
    with _tasks_lock:
        return _tasks.get(task_id)

def submit_async_task(name: str, func, *args, **kwargs) -> str:
    """
    Submits a task with progress tracking to the background executor.
    The wrapped function must accept task_id as its first parameter.
    """
    task_id = create_task(name)

    def task_wrapper():
        try:
            update_task(task_id, progress=0, status="processing", message="Task started")
            func(task_id, *args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            update_task(task_id, progress=100, status="failed", message=f"Task failed: {str(e)}", error=str(e))

    executor.submit(task_wrapper)
    return task_id

