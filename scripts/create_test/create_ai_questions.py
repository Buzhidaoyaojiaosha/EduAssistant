#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import datetime
import random
from peewee import *

# 导入模型
from app.models.user import *
from app.models.course import *
from app.models.assignment import *
from app.models.learning_data import *
from app.models.knowledge_base import *
from app.models.NewAdd import Question, AIQuestion

# 当前参考日期
CURRENT_DATE = datetime.datetime(2025, 3, 20, 9, 42, 30)

def setup_database():
    """连接到数据库。"""
    db.connect()
    print("已连接到数据库。")

def get_courses():
    """获取所有课程。"""
    courses = Course.select().where(Course.is_active == True)
    return list(courses)

def get_assignments():
    """获取所有作业。"""
    assignments = Assignment.select()
    return list(assignments)

def get_questions():
    """获取所有题目。"""
    questions = Question.select()
    return list(questions)

def create_ai_questions():
    """创建AI生成题目数据。"""
    courses = get_courses()
    assignments = get_assignments()
    questions = get_questions()
    
    if not courses:
        print("数据库中没有找到课程。请先运行create_courses_knowledge_points.py。")
        return []
    
    if not assignments:
        print("数据库中没有找到作业。请先运行create_enrollments_assignments.py。")
        return []
    
    if not questions:
        print("数据库中没有找到题目。请先运行create_questions_wrongbooks.py。")
        return []
    
    ai_questions = []
    
    print("\n创建AI生成题目数据...")
    
    # 为每个课程创建一些AI题目
    for course in courses:
        # 获取该课程的作业
        course_assignments = [a for a in assignments if a.course == course]
        if not course_assignments:
            continue
        
        # 为每个作业创建2-5个AI题目
        for assignment in course_assignments:
            num_ai_questions = random.randint(2, 5)
            
            for i in range(num_ai_questions):
                # 随机选择一个原题目作为参考
                original_question = random.choice(questions)
                
                # 根据原题目类型生成AI题目
                question_type = original_question.status
                
                # 创建时间（在过去30天内）
                created_time = CURRENT_DATE - datetime.timedelta(
                    days=random.randint(1, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # 根据题目类型生成AI题目内容和答案
                if question_type == 1:  # 选择题
                    question_name = f"{course.name}AI选择题{i+1}"
                    context = f"在{course.name}中，关于{original_question.context.split('关于')[1].split('，')[0] if '关于' in original_question.context else '相关知识点'}，下列说法正确的是：\n"
                    context += "A. AI生成的选项A描述\nB. AI生成的选项B描述\nC. AI生成的选项C描述\nD. AI生成的选项D描述"
                    answer = random.choice(['A', 'B', 'C', 'D'])
                    analysis = f"AI解析：选项{answer}是正确的，因为这是基于原题目的AI生成解析。"
                
                elif question_type == 2:  # 判断题
                    question_name = f"{course.name}AI判断题{i+1}"
                    context = f"AI生成的判断题：{original_question.context.split('是')[0] if '是' in original_question.context else '相关概念'}是{course.name}中的核心概念。（判断对错）"
                    answer = random.choice(['对', '错'])
                    analysis = f"AI解析：该说法{answer}，这是基于原题目的AI生成解析。"
                
                else:  # 简答题
                    question_name = f"{course.name}AI简答题{i+1}"
                    context = f"请详细阐述{course.name}中的{original_question.context.split('中的')[1].split('概念')[0] if '中的' in original_question.context else '相关知识点'}概念及其应用。"
                    answer = "AI生成的标准答案应包含以下要点：\n1. 概念定义\n2. 主要特性\n3. 应用场景\n4. 优缺点分析"
                    analysis = "AI评分要点：\n- 概念理解准确性\n- 论述逻辑性\n- 例子恰当性\n- 见解深度"
                
                try:
                    # 创建AI题目
                    ai_question = AIQuestion.create(
                        original_question=original_question,
                        question_name=question_name,
                        assignment=assignment,
                        course=course,
                        context=context,
                        answer=answer,
                        analysis=analysis,
                        status=question_type,
                        created_time=created_time,
                        is_approved=True  # 设置为已审核通过
                    )
                    
                    print(f"创建AI题目：{question_name} - {assignment.title}")
                    ai_questions.append(ai_question)
                        
                except Exception as e:
                    print(f"创建AI题目时出错：{e}")
    
    print(f"共创建了 {len(ai_questions)} 个AI生成题目。")
    return ai_questions

def main():
    setup_database()
    
    # 创建AI生成题目
    ai_questions = create_ai_questions()
    
    print("\nAI题目数据创建完成！")
    print(f"创建了 {len(ai_questions)} 个AI生成题目。")

if __name__ == "__main__":
    main() 