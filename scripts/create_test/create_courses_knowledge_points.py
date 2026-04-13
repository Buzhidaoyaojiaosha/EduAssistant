#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import random
from peewee import *

# Import models from your existing code
from app.models.user import *
from app.models.course import *
from app.models.assignment import *
from app.models.learning_data import *
from app.models.knowledge_base import *

def setup_database():
    """Connect to the database."""
    db.connect()
    print("Connected to database.")

def get_teachers():
    """Get all users with teacher role."""
    teachers = User.select().join(UserRole).join(Role).where(Role.name == 'teacher')
    return list(teachers)

def create_courses_with_knowledge_points():
    """Create courses and associated knowledge points."""
    # Get teachers to assign to courses
    teachers = get_teachers()
    if not teachers:
        print("No teachers found in the database. Please run create_test_users.py first.")
        return
    
    # Define courses with their knowledge point structures
    courses_data = [
        {
            'name': 'Introduction to Computer Science',
            'code': 'CS101',
            'description': 'This course introduces fundamental concepts of computer science for students with little or no programming experience.',
            'teacher': teachers[0],  # prof_zhang
            'knowledge_points': [
                {
                    'name': 'Programming Basics',
                    'description': 'Understanding fundamental programming concepts',
                    'children': [
                        {'name': 'Variables and Data Types', 'description': 'Understanding different data types and variable declarations'},
                        {'name': 'Control Structures', 'description': 'Loops, conditionals, and program flow'},
                        {'name': 'Functions', 'description': 'Function declaration and usage'},
                    ]
                },
                {
                    'name': 'Algorithms',
                    'description': 'Introduction to algorithmic thinking',
                    'children': [
                        {'name': 'Sorting Algorithms', 'description': 'Basic sorting techniques'},
                        {'name': 'Searching Algorithms', 'description': 'Methods for searching data'},
                    ]
                },
                {
                    'name': 'Data Structures',
                    'description': 'Basic data structures for organizing information',
                    'children': [
                        {'name': 'Arrays', 'description': 'Working with fixed-size collections'},
                        {'name': 'Linked Lists', 'description': 'Dynamic data structures'},
                        {'name': 'Stacks and Queues', 'description': 'LIFO and FIFO structures'},
                    ]
                }
            ]
        },
        {
            'name': 'Database Systems',
            'code': 'CS305',
            'description': 'Introduction to database design, implementation, and management.',
            'teacher': teachers[1],  # dr_liu
            'knowledge_points': [
                {
                    'name': 'Relational Database Design',
                    'description': 'Designing effective relational databases',
                    'children': [
                        {'name': 'Entity-Relationship Model', 'description': 'Modeling entities and their relationships'},
                        {'name': 'Normalization', 'description': 'Process of organizing data to reduce redundancy'},
                        {'name': 'Schema Design', 'description': 'Creating efficient database schemas'},
                    ]
                },
                {
                    'name': 'SQL',
                    'description': 'Structured Query Language for database interaction',
                    'children': [
                        {'name': 'Data Manipulation', 'description': 'INSERT, UPDATE, DELETE operations'},
                        {'name': 'Data Queries', 'description': 'SELECT statements and complex queries'},
                        {'name': 'Aggregation and Grouping', 'description': 'GROUP BY, HAVING clauses'},
                    ]
                },
                {
                    'name': 'Transaction Management',
                    'description': 'Managing database transactions',
                    'children': [
                        {'name': 'ACID Properties', 'description': 'Atomicity, Consistency, Isolation, Durability'},
                        {'name': 'Concurrency Control', 'description': 'Managing simultaneous access to data'},
                    ]
                }
            ]
        },
        {
            'name': 'Machine Learning Fundamentals',
            'code': 'AI201',
            'description': 'Introduction to machine learning algorithms and applications.',
            'teacher': teachers[2],  # prof_wang
            'knowledge_points': [
                {
                    'name': 'Supervised Learning',
                    'description': 'Learning from labeled data',
                    'children': [
                        {'name': 'Classification', 'description': 'Predicting discrete categories'},
                        {'name': 'Regression', 'description': 'Predicting continuous values'},
                        {'name': 'Evaluation Metrics', 'description': 'Methods to assess model performance'},
                    ]
                },
                {
                    'name': 'Unsupervised Learning',
                    'description': 'Learning patterns from unlabeled data',
                    'children': [
                        {'name': 'Clustering', 'description': 'Grouping similar data points'},
                        {'name': 'Dimensionality Reduction', 'description': 'Reducing feature space'},
                    ]
                },
                {
                    'name': 'Neural Networks',
                    'description': 'Foundations of neural networks',
                    'children': [
                        {'name': 'Perceptrons', 'description': 'Basic neural network building blocks'},
                        {'name': 'Backpropagation', 'description': 'Training neural networks'},
                        {'name': 'Activation Functions', 'description': 'Non-linearities in neural networks'},
                    ]
                }
            ]
        },
        {
            'name': 'Calculus I',
            'code': 'MATH101',
            'description': 'Introduction to differential and integral calculus.',
            'teacher': teachers[3],  # ms_chen
            'knowledge_points': [
                {
                    'name': 'Limits and Continuity',
                    'description': 'Understanding the concept of limits',
                    'children': [
                        {'name': 'Definition of Limits', 'description': 'Formal and intuitive definitions'},
                        {'name': 'Properties of Limits', 'description': 'Rules for calculating limits'},
                        {'name': 'Continuity of Functions', 'description': 'Continuous and discontinuous functions'},
                    ]
                },
                {
                    'name': 'Derivatives',
                    'description': 'Rates of change and differentiation',
                    'children': [
                        {'name': 'Definition of Derivative', 'description': 'The derivative as a limit'},
                        {'name': 'Differentiation Rules', 'description': 'Product, quotient, and chain rules'},
                        {'name': 'Applications of Derivatives', 'description': 'Optimization and related rates'},
                    ]
                },
                {
                    'name': 'Integration',
                    'description': 'Antiderivatives and the definite integral',
                    'children': [
                        {'name': 'Indefinite Integrals', 'description': 'Finding antiderivatives'},
                        {'name': 'Definite Integrals', 'description': 'Area under curves'},
                        {'name': 'Fundamental Theorem of Calculus', 'description': 'Connecting differentiation and integration'},
                    ]
                }
            ]
        },
        {
            'name': 'Digital Electronics',
            'code': 'EE202',
            'description': 'Study of digital circuits and systems.',
            'teacher': teachers[4],  # dr_li
            'knowledge_points': [
                {
                    'name': 'Boolean Algebra',
                    'description': 'Mathematical foundation of digital logic',
                    'children': [
                        {'name': 'Logic Gates', 'description': 'AND, OR, NOT, and other basic gates'},
                        {'name': 'Boolean Functions', 'description': 'Expressing logic operations algebraically'},
                        {'name': 'Minimization Techniques', 'description': 'Karnaugh maps and Quine-McCluskey'},
                    ]
                },
                {
                    'name': 'Combinational Circuits',
                    'description': 'Circuits without memory',
                    'children': [
                        {'name': 'Multiplexers and Demultiplexers', 'description': 'Data selection circuits'},
                        {'name': 'Encoders and Decoders', 'description': 'Code conversion circuits'},
                        {'name': 'Adders and Subtractors', 'description': 'Arithmetic circuits'},
                    ]
                },
                {
                    'name': 'Sequential Circuits',
                    'description': 'Circuits with memory elements',
                    'children': [
                        {'name': 'Flip-Flops', 'description': 'Basic memory elements'},
                        {'name': 'Registers', 'description': 'Data storage elements'},
                        {'name': 'Counters', 'description': 'Circuits for counting pulses'},
                    ]
                }
            ]
        }
    ]
    
    created_courses = []
    created_knowledge_points = []
    
    # Create courses and knowledge points
    for course_data in courses_data:
        # Create the course
        try:
            course, created = Course.get_or_create(
                code=course_data['code'],
                defaults={
                    'name': course_data['name'],
                    'description': course_data['description'],
                    'teacher': course_data['teacher'],
                    'is_active': True
                }
            )
            
            if created:
                print(f"Created course: {course.name} ({course.code})")
            else:
                print(f"Course {course.name} already exists.")
            
            created_courses.append(course)
            
            # Create top-level knowledge points for this course
            for kp_data in course_data['knowledge_points']:
                parent_kp, created = KnowledgePoint.get_or_create(
                    name=kp_data['name'],
                    course=course,
                    defaults={
                        'description': kp_data['description'],
                        'parent': None
                    }
                )
                
                if created:
                    print(f"  Created knowledge point: {parent_kp.name}")
                else:
                    print(f"  Knowledge point {parent_kp.name} already exists.")
                
                created_knowledge_points.append(parent_kp)
                
                # Create child knowledge points
                if 'children' in kp_data:
                    for child_data in kp_data['children']:
                        child_kp, created = KnowledgePoint.get_or_create(
                            name=child_data['name'],
                            course=course,
                            parent=parent_kp,
                            defaults={
                                'description': child_data['description']
                            }
                        )
                        
                        if created:
                            print(f"    Created sub-knowledge point: {child_kp.name}")
                        else:
                            print(f"    Sub-knowledge point {child_kp.name} already exists.")
                        
                        created_knowledge_points.append(child_kp)
                
        except Exception as e:
            print(f"Error creating course {course_data['name']}: {e}")
    
    return created_courses, created_knowledge_points

def main():
    #setup_database()
    courses, knowledge_points = create_courses_with_knowledge_points()
    print(f"\nCreated {len(courses)} courses with {len(knowledge_points)} knowledge points!")
    print("Course and knowledge point creation complete!")

if __name__ == "__main__":
    # Import here to avoid circular imports
    main()