#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import random
import json
from peewee import *

from app.models.user import User
from app.models.course import Course
from app.models.teaching_data import TeachingActivity  # 新增的模型
from app.models.user import UserRole  # 确保已导入UserRole

CURRENT_DATE = datetime.datetime(2025, 7, 18, 9, 42, 30)

def setup_database():
    db.connect()
    print("Connected to database.")

def get_teachers():
    """获取所有教师用户"""
    teacher_user_ids = [ur.user_id for ur in UserRole.select().where(UserRole.role_id == 2)]
    return list(User.select().where(User.id.in_(teacher_user_ids)))

def get_courses_by_teacher(teacher):
    """获取教师所授课程"""
    return list(Course.select().where(Course.teacher == teacher))

def create_teaching_activities():
    """为教师批量创建教学活动数据（最近一周内，分散时间，使用timestamp字段）"""
    teachers = get_teachers()
    if not teachers:
        print("No teachers found.")
        return []

    activities = []
    print("\nCreating teaching activities...")

    activity_types = [
        {
            "type": "lecture",
            "duration_range": (1800, 7200),  # 30-120分钟
            "metadata_template": {
                "topic": "Topic_{random_id}",
                "slides_used": random.choice([True, False])
            }
        },
        {
            "type": "grading",
            "duration_range": (900, 3600),  # 15-60分钟
            "metadata_template": {
                "assignment_id": "ass_{random_id}",
                "graded_count": random.randint(10, 50)
            }
        },
        {
            "type": "qa",
            "duration_range": (300, 1800),  # 5-30分钟
            "metadata_template": {
                "question_count": random.randint(1, 10)
            }
        },
        {
            "type": "research",
            "duration_range": (1800, 10800),  # 30-180分钟
            "metadata_template": {
                "research_topic": "Research_{random_id}"
            }
        }
    ]

    # 最近一周的时间范围
    today = CURRENT_DATE
    week_start = today - datetime.timedelta(days=7)
    week_end = today

    for teacher in teachers:
        courses = get_courses_by_teacher(teacher)
        if not courses:
            print(f"Teacher {teacher.name} has no courses.")
            continue

        engagement_level = random.uniform(0.5, 1.0)
        num_activities = int(8 + (20 * engagement_level))

        # 为每个活动分配最近一周内的随机时间
        for _ in range(num_activities):
            activity_type_data = random.choice(activity_types)
            activity_type = activity_type_data["type"]
            course = random.choice(courses)

            # 随机最近一周内的时间
            random_seconds = random.randint(0, int((week_end - week_start).total_seconds()) - 1)
            activity_time = week_start + datetime.timedelta(seconds=random_seconds)

            min_duration, max_duration = activity_type_data["duration_range"]
            duration = random.randint(min_duration, max_duration)

            metadata = activity_type_data["metadata_template"].copy()
            for key, value in metadata.items():
                if isinstance(value, str) and "{random_id}" in value:
                    metadata[key] = value.format(random_id=random.randint(1000, 9999))

            try:
                activity = TeachingActivity.create(
                    teacher=teacher,
                    course=course,
                    activity_type=activity_type,
                    duration=duration,
                    timestamp=activity_time,  # 用timestamp字段
                    metadata=json.dumps(metadata, ensure_ascii=False),
                    created_at=activity_time,
                    updated_at=activity_time
                )
                activities.append(activity)
                if len(activities) % 20 == 0:
                    print(f"Created {len(activities)} teaching activities...")
            except Exception as e:
                print(f"Error creating teaching activity for {teacher.name}: {e}")

    print(f"Created {len(activities)} teaching activities.")
    return activities

def main():
    #setup_database()
    activities = create_teaching_activities()
    print("\nTeaching activity data creation complete!")
    print(f"Created {len(activities)} teaching activities.")

if __name__ == "__main__":
    main()