import json
import re
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify
from app.services.recommend_service import RecommendService

recommend_bp = Blueprint('recommend', __name__, url_prefix='/recommend')


@recommend_bp.route('/')
def index():
    """渲染资源推荐页面"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('recommend/index.html')


def _parse_recommendation(raw):
    """将 LLM 返回的原始字符串解析为合法 JSON"""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        # 尝试直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # 尝试替换单引号后解析
        try:
            return json.loads(raw.replace("'", '"'))
        except json.JSONDecodeError:
            pass
        # 用正则提取 JSON 块
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group().replace("'", '"'))
            except json.JSONDecodeError:
                pass
    # 兜底返回空
    return {"recommendations": []}


@recommend_bp.route('/history', methods=['GET'])
def recommend_by_history():
    raw = RecommendService.get_recommendations_by_history()
    data = _parse_recommendation(raw)
    return jsonify(data)

@recommend_bp.route('/req/<subject>/<chapter>', methods=['GET'])
def recommend_by_req(subject, chapter):
    raw = RecommendService.get_recommendations_by_requirement(subject, chapter)
    data = _parse_recommendation(raw)
    return jsonify(data)
