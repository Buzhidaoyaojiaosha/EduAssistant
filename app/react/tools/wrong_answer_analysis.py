import pandas as pd
from datetime import datetime
from app.models.learning_data import LearningActivity, StudentKnowledgePoint, KnowledgePoint
from app.models.assignment import StudentAssignment, Assignment
from app.models.course import Course
from app.models.user import User  # 新增导入
from app.models.NewAdd import Question,StudentAnswer,WrongBook,QuestionWrongBook  # 新增导入
from app.react.tools_register import register_as_tool

def get_wrong_answers(student_id, course_id=None):
    """获取学生的错题数据。

    Args:
        student_id (int): 学生用户ID
        course_id (int, optional): 课程ID，用于筛选指定课程的错题

    Returns:
        list: 错题列表
    """
    query = (WrongBook
             .select(WrongBook, Question, StudentAnswer, Assignment)
             .join(QuestionWrongBook, on=(WrongBook.wrong_book_id == QuestionWrongBook.wrong_book))
             .join(Question, on=(QuestionWrongBook.question == Question.question_id))
             .join(StudentAnswer, on=(Question.question_id == StudentAnswer.question))
             .join(Assignment, on=(Question.assignment == Assignment.id))
             .where(
                 (StudentAnswer.student_id == student_id)
             ))

    if course_id:
        query = query.where(Assignment.course_id == course_id)

    wrong_answers = []
    for wb in query:
        wrong_answers.append({
            'assignment_id': wb.questionwrongbook.question.assignment.id,
            'title': wb.questionwrongbook.question.assignment.title,
            'question': wb.questionwrongbook.question.context,
            'answer': wb.questionwrongbook.student_answer.commit_answer,
            'correct_answer': wb.questionwrongbook.question.answer,
            'knowledge_point_id': wb.questionwrongbook.question.assignment.knowledge_point_id
        })

    return wrong_answers

def analyze_wrong_answers(wrong_answers):
    """分析错题原因。

    Args:
        wrong_answers (list): 错题列表

    Returns:
        list: 错题分析结果列表
    """
    analysis_results = []
    for answer in wrong_answers:
        knowledge_point = KnowledgePoint.get(KnowledgePoint.id == answer['knowledge_point_id'])
        # 根据数据库表结构调整查询条件
        try:
            mastery_level = StudentKnowledgePoint.get(
                (StudentKnowledgePoint.student_id == answer['student_id']) &
                (StudentKnowledgePoint.knowledge_point_id == answer['knowledge_point_id'])
            ).mastery_level
        except StudentKnowledgePoint.DoesNotExist:
            mastery_level = 0

        if mastery_level < 0.5:
            reason = f"知识点 '{knowledge_point.name}' 掌握不足"
        else:
            reason = "粗心或理解偏差"

        analysis_results.append({
            'assignment_id': answer['assignment_id'],
            'title': answer['title'],
            'question': answer['question'],
            'answer': answer['answer'],
            'correct_answer': answer['correct_answer'],
            'knowledge_point': knowledge_point.name,
            'reason': reason
        })

    return analysis_results

def provide_suggestions(analysis_results):
    """根据错题分析结果提供建议。

    Args:
        analysis_results (list): 错题分析结果列表

    Returns:
        list: 建议列表
    """
    suggestions = []
    for result in analysis_results:
        if result['reason'].startswith("知识点"):
            suggestion = f"建议重新学习知识点 '{result['knowledge_point']}'，并做相关练习。"
        else:
            suggestion = "建议仔细审题，避免粗心错误。"

        suggestions.append({
            'assignment_id': result['assignment_id'],
            'title': result['title'],
            'question': result['question'],
            'answer': result['answer'],
            'correct_answer': result['correct_answer'],
            'knowledge_point': result['knowledge_point'],
            'reason': result['reason'],
            'suggestion': suggestion
        })

    return suggestions