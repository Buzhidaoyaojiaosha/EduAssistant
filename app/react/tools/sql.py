import pymysql
from pymysql import cursors
from dbutils.pooled_db import PooledDB
#from ..config import DevelopmentConfig

class MySQLConnection:
    def __init__(self):
        self.pool = PooledDB(
            creator=pymysql,
            host='localhost',
            port=3306,
            user='root',
            password='rachel',
            database='eduassistant',
            cursorclass=cursors.DictCursor,
            autocommit=True,
            maxconnections=5,
            connect_timeout=10
        )
    
    def get_conn(self):
        return self.pool.connection()

#db_conn = None
db_conn = MySQLConnection()

def sql_select(query: str) -> str:
    with db_conn.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()

def sql_insert(query: str) -> str:
     with db_conn.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.lastrowid

database_schema = """
-- 用户表（学生/教师共用）
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(300) NOT NULL,
    role ENUM('student', 'teacher') NOT NULL,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 知识点体系
CREATE TABLE knowledge_points (
    point_id INT AUTO_INCREMENT PRIMARY KEY,
    point_name VARCHAR(100) NOT NULL,
    parent_point_id INT NULL,  -- 支持知识点层级结构
    description TEXT
);

-- 课程表
CREATE TABLE courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    teacher_id INT NOT NULL,
    description TEXT,
    FOREIGN KEY (teacher_id) REFERENCES users(user_id)
);

-- 学生选课关系
CREATE TABLE student_courses (
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES users(user_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- 作业表
CREATE TABLE assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    publish_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    deadline DATETIME,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- 试题库
CREATE TABLE questions (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT,
    question_text TEXT NOT NULL,
    question_type ENUM('choice', 'fill_blank', 'essay') NOT NULL,
    difficulty FLOAT CHECK (difficulty BETWEEN 0 AND 1),  -- 试题难度系数
    answer TEXT NOT NULL,
    max_score FLOAT,
    analysis TEXT,
    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id)
);

-- 知识点-试题关联表
CREATE TABLE question_points (
    question_id INT NOT NULL,
    point_id INT NOT NULL,
    weight FLOAT DEFAULT 1.0,  -- 知识点权重
    PRIMARY KEY (question_id, point_id),
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    FOREIGN KEY (point_id) REFERENCES knowledge_points(point_id)
);

-- 学生提交作业记录
CREATE TABLE submit_records (
    record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    assignment_id INT NOT NULL,
    submit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INT,  -- 答题耗时
    FOREIGN KEY (student_id) REFERENCES users(user_id),
    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id)
);

-- 学生答题记录
CREATE TABLE answer_records (
    record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    question_id INT NOT NULL,
    submission_id BIGINT NOT NULL,
    answer TEXT NOT NULL,
    -- answer_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- is_correct BOOLEAN,
    score FLOAT,
    -- duration_seconds INT,  -- 答题耗时
    FOREIGN KEY (student_id) REFERENCES users(user_id),
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    FOREIGN KEY (submission_id) REFERENCES submit_records(record_id)
);

-- 在线学习行为表
CREATE TABLE learning_activities (
    activity_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    activity_type ENUM('video', 'exercise', 'reading'),
    start_time DATETIME,
    end_time DATETIME,
    FOREIGN KEY (student_id) REFERENCES users(user_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

"""