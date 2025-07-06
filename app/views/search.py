from flask import *
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.course_service import CourseService
from app.services.rag_service import RAGService
from app.services.user_service import UserService
from app.models.user import User
import os
import uuid

search_bp = Blueprint('search', __name__, url_prefix='/search')


@search_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    query = request.args.get('q', '')
    course_id = request.args.get('course_id')

    if course_id:
        try:
            course_id = int(course_id)
        except:
            course_id = None

    results = []
    if query:
        results = KnowledgeBaseService.search_knowledge(query, course_id)

    # 获取用户课程，用于筛选
    user_id = session['user_id']
    user = User.get_by_id(user_id)

    if UserService.has_role(user, 'teacher'):
        courses = CourseService.get_courses_by_teacher(user_id)
    else:
        courses = CourseService.get_courses_by_student(user_id)

    return render_template('search/index.html',
                           query=query,
                           results=results,
                           courses=courses,
                           selected_course_id=course_id)


@search_bp.route('/api/search')
def api_search():
    """API端点, 用于AJAX搜索请求"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    query = request.args.get('q', '')
    course_id = request.args.get('course_id')
    limit = int(request.args.get('limit', 5))
    keyword_weight = int(request.args.get('keyword_weight', 0.3))

    if course_id:
        try:
            course_id = int(course_id)
        except:
            course_id = None

    results = []
    if query:
        results = KnowledgeBaseService.search_knowledge(query, course_id, limit, keyword_weight)

    # 将结果转换为简单的JSON结构
    simplified_results = []
    for result in results:
        simplified_results.append({
            "id": result["id"],
            "title": result["title"],
            "type": result["type"],
            "content": result["content"],
            "category": result["category"],
            "tags": result["tags"]
        })

    return jsonify({"results": simplified_results})


@search_bp.route('/manage')
def manage_knowledge():
    """管理知识库条目"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = User.get_by_id(user_id)

    # 只有教师和管理员可以管理知识库
    if not (UserService.has_role(user, 'teacher') or UserService.has_role(user, 'admin')):
        flash('您没有权限管理知识库。', 'warning')
        return redirect(url_for('search.index'))

    from app.models.knowledge_base import KnowledgeBase

    if UserService.has_role(user, 'admin'):
        # 管理员可以看到所有条目
        entries = KnowledgeBase.select()
    else:
        # 教师只能看到自己课程的条目
        courses = CourseService.get_courses_by_teacher(user_id)
        course_ids = [course.id for course in courses]

        entries = KnowledgeBase.select().where(
            (KnowledgeBase.course_id.in_(course_ids)) |
            (KnowledgeBase.course_id.is_null())
        )

    return render_template('search/manage.html', entries=entries)


@search_bp.route('/add', methods=['GET', 'POST'])
def add_knowledge():
    """添加知识库条目"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = User.get_by_id(user_id)

    # 权限检查
    if not (UserService.has_role(user, 'teacher') or UserService.has_role(user, 'admin')):
        flash('您没有权限添加知识库条目。', 'warning')
        return redirect(url_for('search.index'))

    # 获取课程列表
    if UserService.has_role(user, 'teacher'):
        courses = CourseService.get_courses_by_teacher(user_id)
    else:
        from app.models.course import Course
        courses = Course.select()

    if request.method == 'POST':
        title = request.form.get('title')
        entry_type = request.form.get('entry_type')
        course_id = request.form.get('course_id')
        category = request.form.get('category')
        tags = request.form.get('tags', '').split(',')
        file = request.files.get('file')  # 正确获取文件对象

        # 初始化content（纯文本内容）
        content = request.form.get('content', '')

        if not course_id:
            course_id = None

        tags = [tag.strip() for tag in tags if tag.strip()]

        try:
            # 处理非纯文字类型
            if entry_type != 'text':
                if not file or file.filename == '':
                    raise ValueError("请选择要上传的文件")

                # 验证文件类型
                allowed_extensions = {
                    'pdf': ['.pdf'],
                    'pptx': ['.ppt', '.pptx'],
                    'other': ['.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.txt',
                              'mp3', '.mp4']
                }
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in allowed_extensions.get(entry_type, []):
                    raise ValueError(f"不支持的文件类型: {ext}")

                # 创建临时文件
                temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                filename = f"{file.filename}"
                temp_path = os.path.join(temp_dir, filename)

                try:
                    # 保存临时文件
                    file.save(temp_path)

                    # 验证文件
                    if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                        raise IOError("文件保存失败")

                    # 上传到OSS
                    file_url = KnowledgeBaseService.upload_file_to_oss(temp_path)
                    content = file_url  # 将文件URL作为内容存储

                    # 处理文件并存储到向量数据库
                    RAGService.process_and_store_file(
                        temp_path,
                        file_url,
                        title,
                        course_id,
                        category,
                        tags
                    )

                except Exception as e:
                    current_app.logger.error(f"文件处理并存储到向量数据库时出错: {str(e)}",exc_info=True)
                    flash("文件处理并存储到向量数据库时出错，请稍后重试。", 'danger')

                finally:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except:
                            current_app.logger.warning(f"临时文件删除失败: {temp_path}")

            # 保存到数据库
            KnowledgeBaseService.add_knowledge(
                title=title,
                type=entry_type,
                content=content,
                course_id=course_id,
                category=category,
                tags=tags,
                source_file=file_url,
                is_chunk=False,
                chunk_index=0,
            )

            flash('知识条目已添加', 'success')
            # 检查是否有返回地址
            return_to = request.form.get('return_to')
            if return_to:
                return redirect(return_to)
            return redirect(url_for('search.manage_knowledge'))


        except ValueError as ve:
            flash(str(ve), 'danger')
        except Exception as e:
            current_app.logger.exception("添加知识条目失败")
            flash(f'添加失败: {str(e)}', 'danger')

    return render_template('search/add_knowledge.html', courses=courses)


@search_bp.route('/edit/<int:knowledge_id>', methods=['GET', 'POST'])
def edit_knowledge(knowledge_id):
    """编辑知识库条目"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = User.get_by_id(user_id)

    # 权限检查
    if not (UserService.has_role(user, 'teacher') or UserService.has_role(user, 'admin')):
        flash('您没有权限编辑知识库条目。', 'warning')
        return redirect(url_for('search.index'))

    from app.models.knowledge_base import KnowledgeBase
    entry = KnowledgeBase.get_by_id(knowledge_id)

    # 获取课程列表
    if UserService.has_role(user, 'teacher'):
        courses = CourseService.get_courses_by_teacher(user_id)

        # 教师只能编辑自己课程的条目或无课程关联的条目
        if entry.course and entry.course.teacher_id != user_id:
            flash('您没有权限编辑该知识库条目。', 'warning')
            return redirect(url_for('search.manage_knowledge'))
    else:
        from app.models.course import Course
        courses = Course.select()

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        course_id = request.form.get('course_id')
        category = request.form.get('category')
        tags = request.form.get('tags', '').split(',')

        if not course_id:
            course_id = None

        # 清理标签
        tags = [tag.strip() for tag in tags if tag.strip()]

        try:
            KnowledgeBaseService.update_knowledge(
                knowledge_id=knowledge_id,
                title=title,
                content=content,
                category=category,
                tags=tags
            )

            # 更新课程关联
            entry.course_id = course_id
            entry.save()

            flash('知识条目已更新。', 'success')
            return redirect(url_for('search.manage_knowledge'))
        except Exception as e:
            flash(f'更新失败: {str(e)}', 'danger')

    return render_template('search/edit_knowledge.html',
                           entry=entry,
                           courses=courses,
                           tags=', '.join(entry.tags) if entry.tags else '')


@search_bp.route('/delete/<int:knowledge_id>', methods=['POST'])
def delete_knowledge(knowledge_id):
    """删除知识库条目"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = User.get_by_id(user_id)
    course_id = request.form.get('course_id')

    # 权限检查
    if not (UserService.has_role(user, 'teacher') or UserService.has_role(user, 'admin')):
        flash('您没有权限删除知识库条目。', 'warning')
        return redirect_back(course_id)

    from app.models.knowledge_base import KnowledgeBase
    entry = KnowledgeBase.get_by_id(knowledge_id)

    # 教师只能删除自己课程的条目或无课程关联的条目
    if UserService.has_role(user, 'teacher') and entry.course and entry.course.teacher_id != user_id:
        flash('您没有权限删除该知识库条目。', 'warning')
        return redirect_back(course_id)

    # 先获取文件URL以便之后删除 - 从content字段获取
    file_url = entry.content if hasattr(entry, 'content') else None

    success = KnowledgeBaseService.delete_knowledge(knowledge_id)

    if success and entry.type != 'text':
        # 如果知识条目删除成功且content是OSS文件URL，则删除OSS上的文件
        if file_url and file_url.startswith('http'):
            try:
                KnowledgeBaseService.delete_file_from_oss(file_url)
                RAGService.delete_chunks_by_source_url(file_url)

            except Exception as e:
                print(f"删除OSS文件失败: {str(e)}")
                # 这里可以选择记录日志但不影响主流程

        flash('知识条目已删除。', 'success')
    else:
        flash('删除失败。', 'danger')

    return redirect(url_for('search.manage_knowledge'))


def redirect_back(course_id=None):
    """根据来源重定向"""
    if course_id:
        return redirect(url_for('course.view', course_id=course_id))
    return redirect(url_for('search.manage_knowledge'))
