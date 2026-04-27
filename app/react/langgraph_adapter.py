import json
import os
from typing import Any, Optional, get_type_hints

from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field, create_model

from app.react.tools_register import student_tools, teacher_tools, admin_tools
from app.services.user_service import UserService

# 工具中文名映射（用于前端状态显示）
TOOL_NAMES_CN = {
    'search_docs': '搜索文档',
    'bocha_search': '联网搜索',
    'baidu_search': '百度搜索',
    'get_courses_by_teacher_id': '查询课程信息',
    'get_courses_by_student': '查询已选课程',
    'get_students_by_course': '查询课程学生',
    'get_student_knowledge_mastery': '查询知识点掌握情况',
    'get_course_knowledge_mastery': '查询课程掌握度',
    'get_student_activity_summary': '查询学习活动',
    'get_course_knowledge_points': '查询知识点',
    'detect_learning_issues': '检测学习问题',
    'get_student_assignments': '查询学生作业',
    'get_course_assignments': '查询课程作业',
    'get_student_answers': '查询答题详情',
    'auto_grade_assignment': '自动批改作业',
    'grade_assignment': '批改作业',
    'grade_student_answer': '评分',
    'get_assignment_statistics': '查询作业统计',
    'learning_analyze': '分析学习数据',
    'generate_assessment_with_ai': '生成试题',
    'generate_teaching_material': '生成教学材料',
    'generate_questions_with_ai': 'AI生成题目',
    'generate_questions': '生成题目',
    'generate_exam': '生成试卷',
    'generate_outline': '生成教学大纲',
    'save_teaching_material': '保存教学材料',
    'analyze': '错题分析',
    'create_knowledge_point': '创建知识点',
    'get_knowledge_point': '查询知识点',
    'generate_task': '生成每日任务',
    'generate_homework': '生成作业内容',
    'generate_comment': '生成学生评语',
    'train_course_model': '训练认知诊断模型',
    'predict_student_mastery': '预测掌握度',
    'update_course_mastery': '更新掌握度',
    'analyze_course_difficulty': '分析课程难度',
    'get_course_mastery_summary': '掌握度汇总',
}

SYSTEM_PROMPT_TEMPLATE = (
    "你是一个教育领域的AI助手。你的目标是帮助用户完成教学、课程或学习相关的任务。\n\n"
    "可用工具已经列出，请根据用户的问题选择合适的工具。\n\n"
    "指示：\n"
    "1. 优先使用系统内部数据工具（课程、作业、学习行为、知识点等）获取事实。\n"
    "2. 只有在以下场景才允许使用外部搜索工具（如 bocha_search、baidu_search）：\n"
    "   - 用户明确要求联网检索最新信息；\n"
    "   - 内部工具已尝试但无法提供所需信息。\n"
    "3. 如果查询属于校内业务数据（学生/教师/课程/作业/知识点/学习记录），不要先调用外部搜索。\n"
    "4. 在需要更多信息时使用工具，可以一次性调用多个工具。\n"
    "5. 始终将推理建立在工具使用的实际观察结果上。\n"
    "6. 如果工具返回无结果或失败，请承认这一点并考虑使用不同的工具或方法。\n"
    "7. 如果用户使用中文提问，用中文回答。如果用户用英文提问，用英文回答。\n\n"
    "用户信息：{user_info}"
)

# 类型字符串 → Python 类型映射
_TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "List": list,
    "Dict": dict,
    "Any": Any,
}


def _resolve_type(type_str: str) -> type:
    """将 tools_register 中的类型字符串转为 Python 类型。"""
    return _TYPE_MAP.get(type_str, Any)


def _build_args_schema(name: str, parameters: dict) -> type[BaseModel]:
    """根据 tools_register 的 parameters 字典构建 Pydantic schema。"""
    if not parameters:
        return create_model(f"{name}_Input", __base__=BaseModel)

    fields = {}
    for param_name, meta in parameters.items():
        param_type = _resolve_type(meta.get("type", "Any"))
        desc = meta.get("description", "") or ""
        # 所有参数标记为可选（带 None 默认值），避免 LLM 忘传可选参数时报错
        fields[param_name] = (
            Optional[param_type],
            Field(default=None, description=desc),
        )

    return create_model(f"{name}_Input", **fields, __base__=BaseModel)


def _make_tool(name: str, info: dict) -> StructuredTool:
    """将 tools_register 中的工具条目转换为 LangChain StructuredTool。"""
    executor = info["function"]
    description = info.get("description") or f"Tool: {name}"
    parameters = info.get("parameters", {})
    args_schema = _build_args_schema(name, parameters)

    def _run(**kwargs) -> str:
        # 过滤掉 None 值的可选参数
        params = {k: v for k, v in kwargs.items() if v is not None}
        try:
            result = executor(params)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str, indent=2)
        except Exception as e:
            return f"执行 {name} 时出错: {e}"

    return StructuredTool.from_function(
        func=_run,
        name=name,
        description=description,
        args_schema=args_schema,
    )


def get_tools_for_role(role: str) -> list:
    """根据用户角色返回对应的 LangChain 工具列表。"""
    if role == "student":
        source = student_tools
    elif role == "teacher":
        source = teacher_tools
    else:
        source = admin_tools
    return [_make_tool(name, info) for name, info in source.items()]


def create_agent(role: str):
    """创建 LangGraph ReAct agent。"""
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        temperature=0,
    )
    tools = get_tools_for_role(role)
    checkpointer = MemorySaver()
    return create_react_agent(llm, tools, checkpointer=checkpointer)


def run_langgraph(query: str, role: str, history_messages, chat_id: int, user_id: int) -> str:
    """LangGraph agent 入口函数。"""
    agent = create_agent(role)

    user_info = json.dumps(
        UserService.get_user_info(user_id),
        ensure_ascii=False,
        indent=2,
    )
    system_msg = SYSTEM_PROMPT_TEMPLATE.format(user_info=user_info)

    # 构建消息列表
    messages = [("system", system_msg)]

    # 添加历史消息
    if history_messages:
        for msg in history_messages:
            if msg.role in ("user", "assistant"):
                messages.append((msg.role, msg.content))

    # 添加当前用户提问（如果历史中最后一条不是当前提问）
    if not history_messages or not (
        history_messages[-1].role == "user"
        and history_messages[-1].content == query
    ):
        messages.append(("user", query))

    config = {"configurable": {"thread_id": str(chat_id)}}
    result = agent.invoke(
        {"messages": messages},
        config=config,
    )

    # 提取最后一条有内容的 AI 消息
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.content and msg.type == "ai":
            return msg.content

    return "抱歉，无法生成回复。"


def stream_langgraph(query: str, role: str, history_messages, chat_id: int, user_id: int):
    """LangGraph agent 流式入口，yield 中间状态事件和最终结果。

    Yields:
        dict: 事件对象
        - {"step": "thinking", "message": "..."}  — AI 正在思考
        - {"step": "tool", "tool": "name", "message": "..."}  — 正在调用工具
        - {"step": "generating", "message": "正在生成回答..."}  — 生成最终回答
        - {"step": "result", "content": "..."}  — 最终结果
        - {"step": "error", "message": "..."}  — 错误
    """
    agent = create_agent(role)

    user_info = json.dumps(
        UserService.get_user_info(user_id),
        ensure_ascii=False,
        indent=2,
    )
    system_msg = SYSTEM_PROMPT_TEMPLATE.format(user_info=user_info)

    messages = [("system", system_msg)]
    if history_messages:
        for msg in history_messages:
            if msg.role in ("user", "assistant"):
                messages.append((msg.role, msg.content))
    if not history_messages or not (
        history_messages[-1].role == "user"
        and history_messages[-1].content == query
    ):
        messages.append(("user", query))

    config = {"configurable": {"thread_id": str(chat_id)}}

    try:
        final_answer = None
        for chunk in agent.stream({"messages": messages}, config=config):
            if "agent" in chunk:
                agent_msgs = chunk["agent"].get("messages", [])
                has_tool_calls = False
                for msg in agent_msgs:
                    if msg.type == "ai":
                        if msg.tool_calls:
                            has_tool_calls = True
                            for tc in msg.tool_calls:
                                tool_name = tc["name"]
                                cn_name = TOOL_NAMES_CN.get(tool_name, tool_name)
                                yield {"step": "tool", "tool": tool_name, "message": f"正在{cn_name}..."}
                        elif msg.content:
                            final_answer = msg.content
                if not has_tool_calls and final_answer:
                    yield {"step": "generating", "message": "正在生成回答..."}
            elif "tools" in chunk:
                yield {"step": "thinking", "message": "正在分析结果..."}

        if final_answer:
            yield {"step": "result", "content": final_answer}
        else:
            yield {"step": "result", "content": "抱歉，无法生成回复。"}

    except Exception as e:
        yield {"step": "error", "message": str(e)}
