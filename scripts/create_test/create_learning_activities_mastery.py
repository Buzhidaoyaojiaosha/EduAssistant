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
# Current reference date - using the provided date
CURRENT_DATE = datetime.datetime(2025, 7, 18, 9, 42, 30)

def setup_database():
    """Connect to the database."""
    db.connect()
    print("Connected to database.")

def get_enrollments():
    """Get all active student enrollments."""
    enrollments = StudentCourse.select().where(StudentCourse.is_active == True)
    return list(enrollments)

def get_assignment_performance(student, course, knowledge_point):
    """Calculate student performance on assignments related to a knowledge point."""
    # Get assignments linked to this knowledge point
    assignments = (Assignment
                  .select()
                  .join(AssignmentKnowledgePoint)
                  .where(
                      (AssignmentKnowledgePoint.knowledge_point == knowledge_point) &
                      (Assignment.course == course)
                  ))
    
    # Get student submissions for these assignments
    submissions = (StudentAssignment
                  .select()
                  .where(
                      (StudentAssignment.student == student) &
                      (StudentAssignment.assignment.in_(assignments)) &
                      (StudentAssignment.final_score.is_null(False)) &
                      (StudentAssignment.status >= 2)  # 已批改或有评语
                  ))
    
    if not submissions:
        return None
    
    # Calculate average performance (as percentage of total points)
    total_score = 0
    total_possible = 0
    
    for submission in submissions:
        total_score += submission.final_score
        total_possible += submission.total_score
    
    if total_possible == 0:
        return None
    
    return total_score / total_possible

def create_learning_activities():
    """Create realistic learning activities for students."""
    enrollments = get_enrollments()
    
    if not enrollments:
        print("No student enrollments found. Please run create_enrollments_assignments.py first.")
        return []
    
    activities = []
    print("\nCreating student learning activities...")
    
    # Activity types with associated metadata
    activity_types = [
        {
            "type": "video_watch",
            "duration_range": (180, 1800),  # 3-30 minutes
            "metadata_template": {
                "video_id": "vid_{random_id}",
                "completion_percentage": None,  # Will be filled dynamically
                "playback_speed": None,  # Will be filled dynamically
                "watched_segments": None  # Will be filled dynamically
            }
        },
        {
            "type": "reading",
            "duration_range": (300, 2400),  # 5-40 minutes
            "metadata_template": {
                "document_id": "doc_{random_id}",
                "pages_read": None,  # Will be filled dynamically
                "total_pages": None,  # Will be filled dynamically
                "completion_percentage": None  # Will be filled dynamically
            }
        },
        {
            "type": "practice_exercise",
            "duration_range": (600, 3600),  # 10-60 minutes
            "metadata_template": {
                "exercise_id": "ex_{random_id}",
                "questions_attempted": None,  # Will be filled dynamically
                "questions_correct": None,  # Will be filled dynamically
                "difficulty_level": None  # Will be filled dynamically
            }
        },
        {
            "type": "discussion_participation",
            "duration_range": (300, 1800),  # 5-30 minutes
            "metadata_template": {
                "thread_id": "thread_{random_id}",
                "posts_created": None,  # Will be filled dynamically
                "posts_read": None,  # Will be filled dynamically
                "characters_typed": None  # Will be filled dynamically
            }
        },
        {
            "type": "quiz_attempt",
            "duration_range": (600, 1800),  # 10-30 minutes
            "metadata_template": {
                "quiz_id": "quiz_{random_id}",
                "score_percentage": None,  # Will be filled dynamically
                "time_per_question": None,  # Will be filled dynamically
                "questions_count": None  # Will be filled dynamically
            }
        }
    ]
    
    # For each enrollment, create multiple learning activities
    for enrollment in enrollments:
        # Get knowledge points for this course
        knowledge_points = list(KnowledgePoint.select().where(KnowledgePoint.course == enrollment.course))
        
        if not knowledge_points:
            print(f"No knowledge points found for {enrollment.course.name}. Skipping learning activities.")
            continue
        
        # Determine student engagement level (affects number of activities)
        engagement_level = random.uniform(0.3, 1.0)
        
        # Create activities spread over the last 90 days
        # More engaged students have more activities
        num_activities = int(10 + (40 * engagement_level))
        
        for _ in range(num_activities):
            # Randomly select an activity type
            activity_type_data = random.choice(activity_types)
            activity_type = activity_type_data["type"]
            
            # Randomly select a knowledge point (or None for general course activities)
            knowledge_point = random.choice(knowledge_points) if random.random() < 0.8 else None
            
            # Determine when this activity occurred (within last 90 days)
            days_ago = random.randint(0, 90)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            activity_time = CURRENT_DATE - datetime.timedelta(
                days=days_ago, hours=hours_ago, minutes=minutes_ago
            )
            
            # Determine duration based on activity type and engagement
            min_duration, max_duration = activity_type_data["duration_range"]
            duration = random.randint(min_duration, max_duration)
            
            # Create activity-specific metadata
            metadata = activity_type_data["metadata_template"].copy()
            
            # Fill in random IDs
            for key, value in metadata.items():
                if isinstance(value, str) and "{random_id}" in value:
                    metadata[key] = value.format(random_id=random.randint(1000, 9999))
            
            # Fill in activity-specific dynamic metadata
            if activity_type == "video_watch":
                metadata["completion_percentage"] = random.randint(30, 100)
                metadata["playback_speed"] = random.choice([0.75, 1.0, 1.25, 1.5, 2.0])
                metadata["watched_segments"] = [[0, random.randint(30, duration)]]
                
            elif activity_type == "reading":
                total_pages = random.randint(10, 50)
                pages_read = random.randint(5, total_pages)
                metadata["pages_read"] = pages_read
                metadata["total_pages"] = total_pages
                metadata["completion_percentage"] = int(100 * pages_read / total_pages)
                
            elif activity_type == "practice_exercise":
                total_questions = random.randint(5, 20)
                correct_questions = random.randint(0, total_questions)
                metadata["questions_attempted"] = total_questions
                metadata["questions_correct"] = correct_questions
                metadata["difficulty_level"] = random.choice(["beginner", "intermediate", "advanced"])
                
            elif activity_type == "discussion_participation":
                metadata["posts_created"] = random.randint(0, 5)
                metadata["posts_read"] = random.randint(3, 20)
                metadata["characters_typed"] = random.randint(100, 2000)
                
            elif activity_type == "quiz_attempt":
                questions_count = random.randint(5, 15)
                metadata["score_percentage"] = random.randint(50, 100)
                metadata["time_per_question"] = round(duration / questions_count, 1)
                metadata["questions_count"] = questions_count
            
            try:
                activity = LearningActivity.create(
                    student=enrollment.student,
                    course=enrollment.course,
                    knowledge_point=knowledge_point,
                    activity_type=activity_type,
                    duration=duration,
                    timestamp=activity_time,
                    metadata=json.dumps(metadata),
                    created_at=activity_time,
                    updated_at=activity_time
                )
                
                activities.append(activity)
                
                # Don't print every activity to avoid console spam
                if len(activities) % 50 == 0:
                    print(f"Created {len(activities)} learning activities...")
                
            except Exception as e:
                print(f"Error creating learning activity for {enrollment.student.name}: {e}")
    
    print(f"Created {len(activities)} learning activities.")
    return activities

def create_knowledge_point_mastery():
    """Create knowledge point mastery data for students based on activities and performance."""
    enrollments = get_enrollments()
    
    if not enrollments:
        print("No student enrollments found. Please run create_enrollments_assignments.py first.")
        return []
    
    masteries = []
    print("\nCreating student knowledge point mastery data...")
    
    for enrollment in enrollments:
        # Get knowledge points for this course
        knowledge_points = list(KnowledgePoint.select().where(KnowledgePoint.course == enrollment.course))
        
        if not knowledge_points:
            print(f"No knowledge points found for {enrollment.course.name}. Skipping mastery data.")
            continue
        
        for knowledge_point in knowledge_points:
            # Count activities related to this knowledge point
            activity_count = LearningActivity.select().where(
                (LearningActivity.student == enrollment.student) &
                (LearningActivity.knowledge_point == knowledge_point)
            ).count()
            
            # Get assignment performance for this knowledge point
            assignment_performance = get_assignment_performance(
                enrollment.student, enrollment.course, knowledge_point
            )
            
            # Calculate mastery level based on activities and assignment performance
            if activity_count == 0 and assignment_performance is None:
                # No activities or assignments for this knowledge point
                mastery_level = 0.0
            elif assignment_performance is None:
                # Only activities, no assignments
                mastery_level = min(0.5, activity_count / 20)  # Max 0.5 mastery just from activities
            elif activity_count == 0:
                # Only assignments, no activities
                mastery_level = assignment_performance * 0.8  # Max 0.8 mastery just from assignments
            else:
                # Both activities and assignments
                activity_factor = min(1.0, activity_count / 15)  # Activities contribute up to 40%
                mastery_level = (activity_factor * 0.4) + (assignment_performance * 0.6)
            
            # Add some randomness to mastery level
            mastery_level = max(0.0, min(1.0, mastery_level * random.uniform(0.85, 1.15)))
            
            # Get the most recent interaction with this knowledge point
            last_activity = LearningActivity.select().where(
                (LearningActivity.student == enrollment.student) &
                (LearningActivity.knowledge_point == knowledge_point)
            ).order_by(LearningActivity.timestamp.desc()).first()
            
            last_interaction = last_activity.timestamp if last_activity else None
            
            try:
                mastery, created = StudentKnowledgePoint.get_or_create(
                    student=enrollment.student,
                    knowledge_point=knowledge_point,
                    defaults={
                        'mastery_level': round(mastery_level, 2),
                        'last_interaction': last_interaction,
                        'created_at': CURRENT_DATE - datetime.timedelta(days=random.randint(30, 90)),
                        'updated_at': last_interaction or CURRENT_DATE - datetime.timedelta(days=random.randint(0, 30))
                    }
                )
                
                if created:
                    masteries.append(mastery)
                else:
                    print(f"Mastery data for {enrollment.student.name} on {knowledge_point.name} already exists")
                    masteries.append(mastery)
                
                # Don't print every mastery to avoid console spam
                if len(masteries) % 50 == 0:
                    print(f"Created {len(masteries)} knowledge point mastery records...")
                
            except Exception as e:
                print(f"Error creating mastery data for {enrollment.student.name} on {knowledge_point.name}: {e}")
    
    print(f"Created {len(masteries)} knowledge point mastery records.")
    return masteries

def main():
    #setup_database()
    
    # Step 1: Create learning activities
    activities = create_learning_activities()
    
    # Step 2: Create knowledge point mastery data
    masteries = create_knowledge_point_mastery()
    
    print("\nLearning analytics data creation complete!")
    print(f"Created {len(activities)} learning activities and {len(masteries)} knowledge point mastery records.")
    print("\nAll test data generation complete. Your educational analytics database is now populated with test data.")

if __name__ == "__main__":
    main()