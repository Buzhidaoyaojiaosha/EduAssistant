from flask import Flask
from app.ext import initialize_extensions
from app.config import Config
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 设置上传文件目录
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    print(app.config['UPLOAD_FOLDER'])
    app.config['BASE_DIR'] = os.path.dirname(os.path.dirname(__file__))
    print(app.config['BASE_DIR'])

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # 初始化扩展 (postgres, chroma)
    initialize_extensions()
    
    # 注册蓝图
    from app.views.auth import auth_bp
    from app.views.dashboard import dashboard_bp
    from app.views.admin import admin_bp
    from app.views.analytics import analytics_bp
    from app.views.course import course_bp
    from app.views.search import search_bp
    from app.views.ai_assistant import ai_assistant_bp
    from app.views.recommend import recommend_bp
    from app.views.homework_api import homework_api_bp  # 添加这一行

    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(ai_assistant_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(homework_api_bp)  # 添加这一行

    
    return app