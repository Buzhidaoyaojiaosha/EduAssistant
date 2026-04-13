from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify
from app.services.recommend_service import RecommendService

recommend_bp = Blueprint('recommend', __name__, url_prefix='/recommend')


@recommend_bp.route('/')
def index():
    """渲染资源推荐页面"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('recommend/index.html')


@recommend_bp.route('/history', methods=['GET'])
def recommend_by_history():
    return RecommendService.get_recommendations_by_history()

@recommend_bp.route('/req/<subject>/<chapter>', methods=['GET'])
def recommend_by_req(subject, chapter):
    return RecommendService.get_recommendations_by_requirement(subject, chapter)
