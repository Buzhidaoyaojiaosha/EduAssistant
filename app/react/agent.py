"""LangGraph-based agent. Replaces the legacy hand-written ReAct loop."""
from typing import List

from app.react.langgraph_adapter import run_langgraph
from app.utils.logging import logger


def run(query: str, role: str, history: List, chat_id: int = 0, user_id: int = 0) -> str:
    """运行 AI agent，返回回答文本。

    Args:
        query: 用户提问
        role: 用户角色 (student / teacher / admin)
        history: 历史消息（Peewee ChatMessage 查询结果或列表）
        chat_id: 聊天会话 ID（用于 LangGraph checkpoint）
        user_id: 用户 ID（用于注入用户信息）

    Returns:
        AI 回答字符串
    """
    logger.info(f"Agent run: role={role}, chat_id={chat_id}")
    return run_langgraph(query, role, history, chat_id, user_id)
