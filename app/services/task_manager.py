"""
内存任务队列管理器
使用后台线程执行长时间任务，通过 task_id 轮询状态。
"""
import threading
import time
import uuid
import logging

logger = logging.getLogger(__name__)

_tasks = {}
_lock = threading.Lock()

TASK_EXPIRY_SECONDS = 30 * 60  # 30分钟过期


def create_task():
    """创建一个新任务，返回 task_id"""
    task_id = uuid.uuid4().hex[:12]
    with _lock:
        _tasks[task_id] = {
            'id': task_id,
            'status': 'running',  # running | completed | error
            'result': None,
            'error': None,
            'created_at': time.time()
        }
    return task_id


def update_task(task_id, status, result=None, error=None):
    """更新任务状态"""
    with _lock:
        if task_id in _tasks:
            _tasks[task_id]['status'] = status
            if result is not None:
                _tasks[task_id]['result'] = result
            if error is not None:
                _tasks[task_id]['error'] = error


def get_task(task_id):
    """获取任务状态，返回任务字典或 None"""
    with _lock:
        task = _tasks.get(task_id)
        if task:
            return dict(task)  # 返回副本
    return None


def get_task_result(task_id):
    """获取任务结果（completed 时调用），成功后自动清理任务"""
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return None
        if task['status'] == 'completed':
            result = task['result']
            del _tasks[task_id]
            return result
        elif task['status'] == 'error':
            error = task['error']
            del _tasks[task_id]
            return {'error': error}
        else:
            return {'status': 'running'}
    return None


def cleanup_expired_tasks():
    """清理过期任务"""
    now = time.time()
    with _lock:
        expired = [tid for tid, t in _tasks.items()
                   if now - t['created_at'] > TASK_EXPIRY_SECONDS]
        for tid in expired:
            del _tasks[tid]
    if expired:
        logger.info(f"清理了 {len(expired)} 个过期任务")
