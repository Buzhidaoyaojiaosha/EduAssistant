import datetime
import hashlib
import random
from peewee import *
from werkzeug.security import generate_password_hash

# Assuming these models are imported from your existing code
from app.models.user import *
from app.models.course import *
from app.models.assignment import *
from app.models.learning_data import *
from app.models.knowledge_base import *

def setup_database():
    """Connect to the database."""
    db.connect()
    print("Connected to database.")

def simple_hash(password):
    """Create a simple hash for passwords (for testing only)."""
    return generate_password_hash(password)

def create_users_and_roles():
    """Create teacher and student users and assign appropriate roles."""
    # Fetch existing roles
    try:
        teacher_role = Role.get(Role.name == 'teacher')
        student_role = Role.get(Role.name == 'student')
        print("Found existing roles.")
    except Role.DoesNotExist:
        print("Error: Required roles not found in database.")
        return
    
    # Create teacher users
    teachers = [
        {
            'username': 'prof_zhang',
            'email': 'zhang@university.edu',
            'password': '123456',
            'name': 'Professor Zhang Wei'
        },
        {
            'username': 'dr_liu',
            'email': 'liu@university.edu',
            'password': '123456',
            'name': 'Dr. Liu Mei'
        },
        {
            'username': 'prof_wang',
            'email': 'wang@university.edu',
            'password': '123456',
            'name': 'Professor Wang Jun'
        },
        {
            'username': 'ms_chen',
            'email': 'chen@university.edu',
            'password': '123456',
            'name': 'Ms. Chen Xiu'
        },
        {
            'username': 'dr_li',
            'email': 'li@university.edu',
            'password': '123456',
            'name': 'Dr. Li Yun'
        }
    ]
    
    # Create student users (more diverse set)
    students = [
        {'username': 'student001', 'email': 'student001@university.edu', 'password': '123456', 'name': 'Chen Jie'},
        {'username': 'student002', 'email': 'student002@university.edu', 'password': '123456', 'name': 'Li Na'},
        {'username': 'student003', 'email': 'student003@university.edu', 'password': '123456', 'name': 'Wang Lei'},
        {'username': 'student004', 'email': 'student004@university.edu', 'password': '123456', 'name': 'Zhao Min'},
        {'username': 'student005', 'email': 'student005@university.edu', 'password': '123456', 'name': 'Yang Tao'},
        {'username': 'student006', 'email': 'student006@university.edu', 'password': '123456', 'name': 'Wu Fang'},
        {'username': 'student007', 'email': 'student007@university.edu', 'password': '123456', 'name': 'Zhang Yu'},
        {'username': 'student008', 'email': 'student008@university.edu', 'password': '123456', 'name': 'Liu Xin'},
        {'username': 'student009', 'email': 'student009@university.edu', 'password': '123456', 'name': 'Sun Wei'},
        {'username': 'student010', 'email': 'student010@university.edu', 'password': '123456', 'name': 'Ma Ling'},
        {'username': 'student011', 'email': 'student011@university.edu', 'password': '123456', 'name': 'Guo Hui'},
        {'username': 'student012', 'email': 'student012@university.edu', 'password': '123456', 'name': 'Lin Feng'},
        {'username': 'student013', 'email': 'student013@university.edu', 'password': '123456', 'name': 'Zhou Yan'},
        {'username': 'student014', 'email': 'student014@university.edu', 'password': '123456', 'name': 'Xu Ming'},
        {'username': 'student015', 'email': 'student015@university.edu', 'password': '123456', 'name': 'Deng Hong'},
        {'username': 'student016', 'email': 'student016@university.edu', 'password': '123456', 'name': 'Feng Yi'},
        {'username': 'student017', 'email': 'student017@university.edu', 'password': '123456', 'name': 'Cao Jing'},
        {'username': 'student018', 'email': 'student018@university.edu', 'password': '123456', 'name': 'Peng Bo'},
        {'username': 'student019', 'email': 'student019@university.edu', 'password': '123456', 'name': 'Tang Juan'},
        {'username': 'student020', 'email': 'student020@university.edu', 'password': '123456', 'name': 'Hu Qiang'}
    ]
    
    # Create the teachers
    print("Creating teachers...")
    created_teachers = []
    for teacher_data in teachers:
        try:
            user, created = User.get_or_create(
                username=teacher_data['username'],
                defaults={
                    'email': teacher_data['email'],
                    'password_hash': simple_hash(teacher_data['password']),
                    'name': teacher_data['name'],
                    'is_active': True
                }
            )
            
            if created:
                UserRole.get_or_create(
                    user=user,
                    role=teacher_role
                )
                print(f"Created teacher: {user.name}")
                created_teachers.append(user)
            else:
                print(f"Teacher {user.name} already exists")
                created_teachers.append(user)
        except Exception as e:
            print(f"Error creating teacher {teacher_data['name']}: {e}")
    
    # Create the students
    print("\nCreating students...")
    created_students = []
    for student_data in students:
        try:
            user, created = User.get_or_create(
                username=student_data['username'],
                defaults={
                    'email': student_data['email'],
                    'password_hash': simple_hash(student_data['password']),
                    'name': student_data['name'],
                    'is_active': True
                }
            )
            
            if created:
                UserRole.get_or_create(
                    user=user,
                    role=student_role
                )
                print(f"Created student: {user.name}")
                created_students.append(user)
            else:
                print(f"Student {user.name} already exists")
                created_students.append(user)
        except Exception as e:
            print(f"Error creating student {student_data['name']}: {e}")
    
    return created_teachers, created_students

def main():
    #setup_database()
    teachers, students = create_users_and_roles()
    print(f"\nCreated {len(teachers)} teachers and {len(students)} students!")
    print("User creation complete!")

if __name__ == "__main__":
    main()