#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import random
import json
from peewee import *

# Import models
from app.models.user import *
from app.models.course import *
from app.models.assignment import *
from app.models.learning_data import *
from app.models.knowledge_base import *
# Current reference date
CURRENT_DATE = datetime.datetime(2025, 3, 20, 9, 23, 7)

def setup_database():
    """Connect to the database."""
    db.connect()
    print("Connected to database.")

def get_students():
    """Get all users with student role."""
    students = User.select().join(UserRole).join(Role).where(Role.name == 'student')
    return list(students)

def get_courses():
    """Get all active courses."""
    courses = Course.select().where(Course.is_active == True)
    return list(courses)

def enroll_students_in_courses():
    """Enroll students in courses with realistic distribution."""
    students = get_students()
    courses = get_courses()
    
    if not students:
        print("No students found in the database. Please run create_test_users.py first.")
        return []
    
    if not courses:
        print("No courses found in the database. Please run create_courses_knowledge_points.py first.")
        return []
    
    enrollments = []
    
    print("Enrolling students in courses...")
    
    # For each student, enroll in 2-4 courses
    for student in students:
        # Determine how many courses this student takes (2-4)
        num_courses = random.randint(2, min(4, len(courses)))
        # Randomly select courses for this student
        student_courses = random.sample(courses, num_courses)
        
        for course in student_courses:
            # Randomly determine enrollment date (1-120 days ago)
            days_ago = random.randint(1, 120)
            enrollment_date = CURRENT_DATE - datetime.timedelta(days=days_ago)
            
            try:
                enrollment, created = StudentCourse.get_or_create(
                    student=student,
                    course=course,
                    defaults={
                        'is_active': True,
                        'created_at': enrollment_date,
                        'updated_at': enrollment_date
                    }
                )
                
                if created:
                    print(f"Enrolled {student.name} in {course.name}")
                    enrollments.append(enrollment)
                else:
                    print(f"{student.name} already enrolled in {course.name}")
                    enrollments.append(enrollment)
                    
            except Exception as e:
                print(f"Error enrolling {student.name} in {course.name}: {e}")
    
    print(f"Created {len(enrollments)} enrollments.")
    return enrollments

def create_assignments():
    """Create assignments for each course linked to knowledge points."""
    courses = get_courses()
    
    if not courses:
        print("No courses found in the database. Please run create_courses_knowledge_points.py first.")
        return []
    
    assignments = []
    
    # Assignment templates for different courses
    assignment_templates = [
        {"title": "Midterm Exam", "points": 100, "days_before_due": -30}, # Already past due
        {"title": "Final Project", "points": 150, "days_before_due": 30}, # Due in future
        {"title": "Quiz 1", "points": 50, "days_before_due": -60}, # Already past due
        {"title": "Quiz 2", "points": 50, "days_before_due": -15}, # Already past due
        {"title": "Lab Assignment", "points": 75, "days_before_due": 15}, # Due soon
        {"title": "Programming Challenge", "points": 80, "days_before_due": 7}, # Due very soon
        {"title": "Research Paper", "points": 120, "days_before_due": 45}, # Due in future
        {"title": "Group Presentation", "points": 100, "days_before_due": 20}, # Due in future
    ]
    
    print("\nCreating assignments for courses...")
    
    for course in courses:
        # Get knowledge points for this course
        knowledge_points = list(KnowledgePoint.select().where(
            (KnowledgePoint.course == course) & (KnowledgePoint.parent.is_null(False))
        ))
        
        if not knowledge_points:
            print(f"No knowledge points found for {course.name}. Skipping assignment creation.")
            continue
        
        # Choose 3-5 assignment templates randomly for this course
        num_assignments = random.randint(3, min(5, len(assignment_templates)))
        course_assignment_templates = random.sample(assignment_templates, num_assignments)
        
        # Create assignments based on templates
        for idx, template in enumerate(course_assignment_templates):
            # Calculate due date based on current date
            due_date = CURRENT_DATE + datetime.timedelta(days=template["days_before_due"])
            
            # Create a course-specific title
            specific_title = f"{template['title']} - {course.code}"
            
            # Create description using course name and knowledge points
            description = f"This {template['title'].lower()} for {course.name} covers various topics including "
            description += ", ".join([kp.name for kp in random.sample(knowledge_points, min(3, len(knowledge_points)))])
            description += "."
            
            try:
                assignment, created = Assignment.get_or_create(
                    title=specific_title,
                    course=course,
                    defaults={
                        'description': description,
                        'due_date': due_date,
                        'total_points': template['points'],
                        'created_at': due_date - datetime.timedelta(days=random.randint(20, 40)),
                        'updated_at': due_date - datetime.timedelta(days=random.randint(5, 15))
                    }
                )
                
                if created:
                    print(f"Created assignment: {assignment.title} for {course.name}")
                    assignments.append(assignment)
                    
                    # Link this assignment to 2-4 knowledge points
                    num_kps = random.randint(2, min(4, len(knowledge_points)))
                    selected_kps = random.sample(knowledge_points, num_kps)
                    
                    for kp in selected_kps:
                        AssignmentKnowledgePoint.get_or_create(
                            assignment=assignment,
                            knowledge_point=kp,
                            defaults={
                                'weight': round(random.uniform(0.5, 1.5), 2),
                                'created_at': assignment.created_at,
                                'updated_at': assignment.created_at
                            }
                        )
                        print(f"  Linked knowledge point: {kp.name}")
                else:
                    print(f"Assignment {assignment.title} already exists.")
                    assignments.append(assignment)
                    
            except Exception as e:
                print(f"Error creating assignment for {course.name}: {e}")
    
    print(f"Created {len(assignments)} assignments.")
    return assignments

def create_student_submissions():
    """Create student assignment submissions with realistic completion patterns."""
    # Get assignments and enrollments
    assignments = list(Assignment.select())
    enrollments = list(StudentCourse.select())
    
    if not assignments:
        print("No assignments found. Please run create_assignments first.")
        return []
    
    if not enrollments:
        print("No student enrollments found. Please run enroll_students_in_courses first.")
        return []
    
    submissions = []
    
    print("\nCreating student submissions for assignments...")
    
    # For each enrollment, create submissions for relevant assignments
    for enrollment in enrollments:
        # Get assignments for this course
        course_assignments = [a for a in assignments if a.course_id == enrollment.course_id]
        
        for assignment in course_assignments:
            # 确定作业状态
            if assignment.due_date < CURRENT_DATE:
                # 过期作业有80%的概率被提交
                if random.random() < 0.8:
                    # 已提交的作业
                    # 85%按时提交，15%迟交
                    is_late = random.random() < 0.15
                    
                    # 计算提交时间
                    if is_late:
                        # 迟交1-48小时
                        hours_late = random.randint(1, 48)
                        submission_time = assignment.due_date + datetime.timedelta(hours=hours_late)
                    else:
                        # 提前1分钟到72小时提交
                        hours_before = random.randint(0, 72)
                        minutes_before = random.randint(1, 59) if hours_before == 0 else 0
                        submission_time = assignment.due_date - datetime.timedelta(
                            hours=hours_before, minutes=minutes_before
                        )
                    
                    # 确定分数
                    max_score = assignment.total_points
                    if is_late:
                        base_score_pct = random.uniform(0.5, 0.85)  # 迟交得分较低
                    else:
                        base_score_pct = random.uniform(0.65, 0.98)  # 按时提交得分较高
                    
                    # 添加随机性模拟学生表现差异
                    final_score = round(max_score * base_score_pct * random.uniform(0.9, 1.1), 1)
                    final_score = min(max_score, max(0, final_score))  # 限制在0和最高分之间
                    
                    # 随机决定状态：已批改或有评语
                    status = random.choice([2, 3])
                    
                    try:
                        submission, created = StudentAssignment.get_or_create(
                            student=enrollment.student,
                            assignment=assignment,
                            defaults={
                                'course': enrollment.course,
                                'status': status,
                                'total_score': assignment.total_points,
                                'final_score': final_score,
                                'work_time': submission_time
                            }
                        )
                        
                        if created:
                            submissions.append(submission)
                        
                    except Exception as e:
                        print(f"Error creating submission for {enrollment.student.name} on {assignment.title}: {e}")
                else:
                    # 未提交的过期作业，状态为待完成
                    try:
                        submission, created = StudentAssignment.get_or_create(
                            student=enrollment.student,
                            assignment=assignment,
                            defaults={
                                'course': enrollment.course,
                                'status': 0,
                                'total_score': assignment.total_points,
                                'final_score': None,
                                'work_time': None
                            }
                        )
                        
                        if created:
                            submissions.append(submission)
                            
                    except Exception as e:
                        print(f"Error creating submission for {enrollment.student.name} on {assignment.title}: {e}")
            else:
                # 未到期的作业
                # 20%的概率已提交但未批改
                if random.random() < 0.2:
                    # 提前提交
                    days_before = random.randint(1, 10)
                    submission_time = CURRENT_DATE - datetime.timedelta(days=days_before)
                    
                    try:
                        submission, created = StudentAssignment.get_or_create(
                            student=enrollment.student,
                            assignment=assignment,
                            defaults={
                                'course': enrollment.course,
                                'status': 1,  # 待批改
                                'total_score': assignment.total_points,
                                'final_score': None,
                                'work_time': submission_time
                            }
                        )
                        
                        if created:
                            submissions.append(submission)
                            
                    except Exception as e:
                        print(f"Error creating submission for {enrollment.student.name} on {assignment.title}: {e}")
                else:
                    # 未提交的未到期作业
                    try:
                        submission, created = StudentAssignment.get_or_create(
                            student=enrollment.student,
                            assignment=assignment,
                            defaults={
                                'course': enrollment.course,
                                'status': 0,  # 待完成
                                'total_score': assignment.total_points,
                                'final_score': None,
                                'work_time': None
                            }
                        )
                        
                        if created:
                            submissions.append(submission)
                            
                    except Exception as e:
                        print(f"Error creating submission for {enrollment.student.name} on {assignment.title}: {e}")
    
    print(f"Created {len(submissions)} student assignment submissions.")
    return submissions

def main():
    #setup_database()
    
    # Step 1: Enroll students in courses
    enrollments = enroll_students_in_courses()
    
    # Step 2: Create assignments for each course
    assignments = create_assignments()
    
    # Step 3: Create student submissions for assignments
    submissions = create_student_submissions()
    
    print("\nEnrollment and assignment setup complete!")
    print(f"Created {len(enrollments)} enrollments, {len(assignments)} assignments, and {len(submissions)} submissions.")

if __name__ == "__main__":
    # Import here to avoid circular imports
    #from models import UserRole, Role
    main()