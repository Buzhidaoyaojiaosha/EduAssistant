#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import random
from peewee import *

# 导入模型
from app.models.user import *
from app.models.course import *
from app.models.assignment import *
from app.models.learning_data import *
from app.models.knowledge_base import *
from app.models.NewAdd import Question, StudentAnswer, Feedback, WrongBook, QuestionWrongBook

# 当前参考日期
CURRENT_DATE = datetime.datetime(2025, 3, 20, 9, 42, 30)

def setup_database():
    """连接到数据库。"""
    db.connect()
    print("已连接到数据库。")

def get_assignments():
    """获取所有作业。"""
    assignments = Assignment.select()
    return list(assignments)

def get_students():
    """获取所有学生用户。"""
    students = User.select().join(UserRole).join(Role).where(Role.name == 'student')
    return list(students)

def get_teachers():
    """获取所有教师用户。"""
    teachers = User.select().join(UserRole).join(Role).where(Role.name == 'teacher')
    return list(teachers)

def get_courses():
    """获取所有课程。"""
    courses = Course.select().where(Course.is_active == True)
    return list(courses)

def get_enrollments():
    """获取所有学生选课记录。"""
    enrollments = StudentCourse.select().where(StudentCourse.is_active == True)
    return list(enrollments)

def get_knowledge_points():
    """获取所有知识点。"""
    knowledge_points = KnowledgePoint.select()
    return list(knowledge_points)

def create_questions():
    """创建试题数据。"""
    assignments = get_assignments()
    knowledge_points = get_knowledge_points()
    
    if not assignments:
        print("数据库中没有找到作业。请先运行create_enrollments_assignments.py。")
        return []
    
    if not knowledge_points:
        print("数据库中没有找到知识点。请先运行create_courses_knowledge_points.py。")
        return []
    
    questions = []
    
    # 题目类型
    question_types = [1, 2, 3, 4]  # 1:选择题, 2:判断题, 3:简答题,4:编程题
    
    print("\n创建试题数据...")
    
    # 为每个作业创建3-8个题目
    for assignment in assignments:
        # 获取与该作业相关的知识点
        assignment_kps = list(AssignmentKnowledgePoint.select().where(
            AssignmentKnowledgePoint.assignment == assignment
        ))
        
        if not assignment_kps:
            print(f"作业 {assignment.title} 没有关联的知识点，跳过创建题目。")
            continue
        
        # 确定该作业的题目数量
        num_questions = random.randint(3, 8)
        
        for i in range(num_questions):
            # 随机选择题目类型
            question_type = random.choice(question_types)
            
            # 创建时间（在过去30天内）
            created_time = CURRENT_DATE - datetime.timedelta(
                days=random.randint(1, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # 根据题目类型生成题目内容和答案
            if question_type == 1:  # 选择题
                question_name = f"{assignment.course.name}选择题{i+1}"
                context = f"在{assignment.course.name}中，关于{random.choice(assignment_kps).knowledge_point.name}，下列说法正确的是：\n"
                context += "A. 选项A描述\nB. 选项B描述\nC. 选项C描述\nD. 选项D描述"
                answer = random.choice(['A', 'B', 'C', 'D'])
                analysis = f"解析：选项{answer}是正确的，因为..."
                score = random.choice([2, 3, 5])
            
            elif question_type == 2:  # 判断题
                question_name = f"{assignment.course.name}判断题{i+1}"
                context = f"{random.choice(assignment_kps).knowledge_point.name}是{assignment.course.name}中的核心概念。（判断对错）"
                answer = random.choice(['对', '错'])
                analysis = f"解析：该说法{answer}，因为..."
                score = random.choice([2, 3])
            
            # elif question_type == 3:  # 填空题
            #     question_name = f"{assignment.course.name}填空题{i+1}"
            #     context = f"在{assignment.course.name}中，_____是{random.choice(assignment_kps).knowledge_point.name}的重要特性。"
            #     answer = "填空答案"
            #     analysis = "解析：这个特性很重要是因为..."
            #     score = random.choice([3, 5])
            else:  # 简答题
                question_name = f"{assignment.course.name}简答题{i+1}"
                context = f"请详细阐述{assignment.course.name}中的{random.choice(assignment_kps).knowledge_point.name}概念及其应用。"
                answer = "标准答案应包含以下要点：\n1. 概念定义\n2. 主要特性\n3. 应用场景\n4. 优缺点分析"
                analysis = "评分要点：\n- 概念理解准确性\n- 论述逻辑性\n- 例子恰当性\n- 见解深度"
                score = random.choice([10, 15, 20])
            
            try:
                # 创建题目
                question = Question.create(
                    question_name=question_name,
                    assignment=assignment,
                    course=assignment.course,
                    context=context,
                    answer=answer,
                    analysis=analysis,
                    score=score,
                    status=question_type,
                    created_time=created_time
                )
                
                print(f"创建题目：{question_name} - {assignment.title}")
                questions.append(question)
                    
            except Exception as e:
                print(f"创建题目时出错：{e}")
    
    print(f"共创建了 {len(questions)} 个题目。")
    return questions

def create_student_answers():
    """创建学生答题记录。"""
    students = get_students()
    questions = list(Question.select())
    
    if not students:
        print("数据库中没有找到学生。请先运行create_test_users.py。")
        return []
    
    if not questions:
        print("数据库中没有找到题目。请先运行create_questions函数。")
        return []
    
    student_answers = []
    
    print("\n创建学生答题记录...")
    
    # 获取所有已提交的学生作业
    student_assignments = list(StudentAssignment.select().where(
        (StudentAssignment.status >= 1) &  # 待批改、已批改或有评语
        (StudentAssignment.work_time.is_null(False))
    ))
    
    if not student_assignments:
        print("没有找到学生提交的作业。请先运行create_enrollments_assignments.py。")
        return []
    
    for student_assignment in student_assignments:
        # 获取该作业的所有题目
        assignment_questions = list(Question.select().where(Question.assignment == student_assignment.assignment))
        
        if not assignment_questions:
            continue
        
        # 为每个题目创建学生答案
        for question in assignment_questions:
            # 80%的概率学生会回答这个题目
            if random.random() < 0.8:
                # 根据题目类型生成学生答案
                if question.status == 0:  # 主观题
                    # 生成不同质量的论述答案
                    quality = random.random()
                    if quality > 0.8:
                        commit_answer = "优秀答案：完整阐述了概念定义、特性、应用场景和优缺点分析，并有独到见解。"
                        earned_score = question.score * random.uniform(0.9, 1.0)
                    elif quality > 0.6:
                        commit_answer = "良好答案：基本阐述了概念定义、特性和应用场景，但分析不够深入。"
                        earned_score = question.score * random.uniform(0.7, 0.9)
                    elif quality > 0.4:
                        commit_answer = "一般答案：概念理解基本正确，但缺少详细分析和应用场景讨论。"
                        earned_score = question.score * random.uniform(0.5, 0.7)
                    else:
                        commit_answer = "较差答案：概念理解有误，论述不完整，缺乏逻辑性。"
                        earned_score = question.score * random.uniform(0.3, 0.5)
                
                elif question.status == 1:  # 选择题
                    # 70%概率答对，30%概率答错
                    if random.random() < 0.7:
                        commit_answer = question.answer
                        earned_score = question.score
                    else:
                        options = ['A', 'B', 'C', 'D']
                        options.remove(question.answer)
                        commit_answer = random.choice(options)
                        earned_score = 0
                
                elif question.status == 2:  # 判断题
                    # 65%概率答对，35%概率答错
                    if random.random() < 0.65:
                        commit_answer = question.answer
                        earned_score = question.score
                    else:
                        commit_answer = '错' if question.answer == '对' else '对'
                        earned_score = 0
                
                else:  # 填空题
                    # 60%概率完全正确，40%概率部分正确或错误
                    if random.random() < 0.6:
                        commit_answer = question.answer
                        earned_score = question.score
                    else:
                        commit_answer = question.answer + " (有部分错误)"
                        earned_score = question.score * random.uniform(0.3, 0.7)
                
                # 创建答题时间（在作业提交时间前后30分钟内）
                work_time = student_assignment.work_time + datetime.timedelta(
                    minutes=random.randint(-30, 30)
                )
                
                try:
                    student_answer = StudentAnswer.create(
                        student=student_assignment.student,
                        question=question,
                        commit_answer=commit_answer,
                        earned_score=round(earned_score, 1),
                        work_time=work_time
                    )
                    
                    print(f"创建学生答案：{student_assignment.student.name} - {question.question_name}")
                    student_answers.append(student_answer)
                        
                except Exception as e:
                    print(f"创建学生答案时出错：{e}")
    
    print(f"共创建了 {len(student_answers)} 条学生答题记录。")
    return student_answers

def create_feedback():
    """创建教师反馈数据。"""
    teachers = get_teachers()
    
    if not teachers:
        print("数据库中没有找到教师。请先运行create_test_users.py。")
        return []
    
    # 获取所有已完成的学生作业
    student_assignments = list(StudentAssignment.select().where(
        (StudentAssignment.status >= 2) &  # 已批改或有评语
        (StudentAssignment.final_score.is_null(False))
    ))
    
    if not student_assignments:
        print("数据库中没有找到已完成的学生作业。请先运行create_enrollments_assignments.py。")
        return []
    
    feedbacks = []
    
    print("\n创建教师反馈数据...")
    
    # 为70%的学生作业创建教师反馈
    for student_assignment in student_assignments:
        if random.random() < 0.7:
            # 根据学生作业的得分生成反馈内容
            score_percentage = student_assignment.final_score / student_assignment.total_score
            
            if score_percentage >= 0.9:
                comment = random.choice([
                    "优秀的作业！你对课程内容的理解非常深入。",
                    "出色的表现，你的答案非常全面且准确。",
                    "非常好的工作，你的思路清晰，论述有力。",
                    "顶尖水平的作业，展示了你对知识点的完全掌握。"
                ])
            elif score_percentage >= 0.8:
                comment = random.choice([
                    "很好的作业，你对大部分内容都有很好的理解。",
                    "良好的表现，只有少量细节需要改进。",
                    "整体表现不错，继续保持这种学习态度。",
                    "作业完成得很好，只有几个小问题需要注意。"
                ])
            elif score_percentage >= 0.7:
                comment = random.choice([
                    "作业完成得不错，但有些重要概念需要更深入理解。",
                    "基本掌握了课程内容，但还有提升空间。",
                    "答案基本正确，但缺乏深度分析。",
                    "整体表现可以，但需要更加注重细节。"
                ])
            elif score_percentage >= 0.6:
                comment = random.choice([
                    "作业中有一些好的观点，但也有几处重要错误。",
                    "对基本概念有一定理解，但需要更多练习。",
                    "及格水平，但距离良好还有很大差距。",
                    "基础知识掌握不够牢固，建议重新复习相关章节。"
                ])
            else:
                comment = random.choice([
                    "作业中存在多处严重错误，需要重新学习相关内容。",
                    "对课程内容理解不足，建议寻求额外辅导。",
                    "未能达到基本要求，请务必加强学习。",
                    "需要更认真地对待学习，建议重新复习所有相关材料。"
                ])
            
            # 创建时间（在作业提交后1-7天内）
            if student_assignment.work_time:
                created_time = student_assignment.work_time + datetime.timedelta(
                    days=random.randint(1, 7),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            else:
                created_time = CURRENT_DATE - datetime.timedelta(
                    days=random.randint(1, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            
            try:
                feedback = Feedback.create(
                    student=student_assignment.student,
                    assignment=student_assignment.assignment,
                    comment=comment,
                    created_time=created_time
                )
                
                # 更新学生作业状态为"有评语"
                student_assignment.status = 3
                student_assignment.save()
                
                feedbacks.append(feedback)
                
            except Exception as e:
                print(f"创建教师反馈时出错：{e}")
    
    print(f"创建了 {len(feedbacks)} 条教师反馈。")
    return feedbacks

def create_wrong_books():
    """创建错题本数据。"""
    students = get_students()
    courses = get_courses()
    
    if not students:
        print("数据库中没有找到学生。请先运行create_test_users.py。")
        return []
    
    if not courses:
        print("数据库中没有找到课程。请先运行create_courses_knowledge_points.py。")
        return []
    
    wrong_books = []
    
    print("\n创建错题本数据...")
    
    # 获取学生选课记录
    enrollments = get_enrollments()
    
    if not enrollments:
        print("没有找到学生选课记录。请先运行create_enrollments_assignments.py。")
        return []
    
    # 为每个学生的每门课程创建一个错题本
    for enrollment in enrollments:
        # 70%的概率创建错题本
        if random.random() < 0.7:
            wrong_book_name = f"{enrollment.student.name}的{enrollment.course.name}错题集"
            
            # 创建时间（在过去90天内）
            created_time = CURRENT_DATE - datetime.timedelta(
                days=random.randint(1, 90),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            try:
                wrong_book = WrongBook.create(
                    student=enrollment.student,
                    course=enrollment.course,
                    wrong_book_name=wrong_book_name,
                    created_time=created_time
                )
                
                print(f"创建错题本：{wrong_book_name}")
                wrong_books.append(wrong_book)
                
                # 为错题本添加错题
                add_questions_to_wrong_book(wrong_book)
                    
            except Exception as e:
                print(f"创建错题本时出错：{e}")
    
    print(f"共创建了 {len(wrong_books)} 个错题本。")
    return wrong_books

def add_questions_to_wrong_book(wrong_book):
    """为错题本添加错题。"""
    # 获取该课程的所有题目
    course_questions = list(Question.select().where(Question.course == wrong_book.course))
    
    if not course_questions:
        print(f"课程 {wrong_book.course.name} 没有题目，跳过添加错题。")
        return []
    
    # 获取该学生的答题记录
    student_answers = list(StudentAnswer.select().where(
        (StudentAnswer.student == wrong_book.student) &
        (StudentAnswer.question.in_([q.id for q in course_questions]))
    ))
    
    # 找出得分低于60%的题目作为错题
    wrong_questions = []
    for answer in student_answers:
        if answer.earned_score < (answer.question.score * 0.6):
            wrong_questions.append(answer.question)
    
    # 如果没有足够的错题，随机选择一些题目作为错题
    if len(wrong_questions) < 3 and course_questions:
        additional_needed = min(3 - len(wrong_questions), len(course_questions))
        potential_additions = [q for q in course_questions if q not in wrong_questions]
        if potential_additions:
            wrong_questions.extend(random.sample(potential_additions, min(additional_needed, len(potential_additions))))
    
    question_wrong_books = []
    
    # 添加错题到错题本
    for question in wrong_questions:
        try:
            # 创建时间（在错题本创建后0-30天内）
            created_time = wrong_book.created_time + datetime.timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            qwb = QuestionWrongBook.create(
                wrong_book=wrong_book,
                question=question,
                created_time=created_time
            )
            
            print(f"  添加错题：{question.question_name}")
            question_wrong_books.append(qwb)
                
        except Exception as e:
            print(f"添加错题时出错：{e}")
    
    print(f"  共添加了 {len(question_wrong_books)} 道错题到错题本 {wrong_book.wrong_book_name}。")
    return question_wrong_books

def main():
    #setup_database()
    
    # 步骤1：创建题目
    questions = create_questions()
    
    # 步骤2：创建学生答题记录
    student_answers = create_student_answers()
    
    # 步骤3：创建教师反馈
    feedbacks = create_feedback()
    
    # 步骤4：创建错题本和错题关联
    wrong_books = create_wrong_books()
    
    print("\n测试数据创建完成！")
    print(f"创建了 {len(questions)} 个题目，{len(student_answers)} 条学生答题记录，")
    print(f"{len(feedbacks)} 条教师反馈，{len(wrong_books)} 个错题本。")

if __name__ == "__main__":
    main()