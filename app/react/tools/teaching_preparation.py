from typing import Dict, List
from datetime import datetime
import os
import tempfile
import io
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from flask import current_app, jsonify
from app.react.tools_register import register_as_tool
from app.utils.logging import logger
from app.models.course import Course
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.course_service import CourseService
from app.utils.llm.deepseek import chat_deepseek
import re

def generate_teaching_outline(course_id: int,selected_knowledge_ids: List[int] = None) -> Dict:
    """生成AI驱动的备课提纲
    
    Args:
        course_id (int): 课程ID
        selected_knowledge_ids (List[int], optional): 选中的知识库ID列表
        
    Returns:
        Dict: 包含生成的备课提纲内容和文件信息
    """
    try:
        course = Course.get_by_id(course_id)
        if not course:
            return {"error": "课程不存在"}
        
        # 1. 获取本课程的知识库资料
        relevant_docs = _get_selected_knowledge_content(course_id, selected_knowledge_ids)
        
        # 2. 构造DeepSeek API提示词
        prompt = f"""
你是一位经验丰富的教师，需要为《{course.name}》课程制作详细的备课提纲。

相关课程资料：
{relevant_docs}

请根据以上课程资料，生成一份完整的备课提纲，包含以下内容：

1. 课程概述（课程性质、地位和作用）
2. 教学目标（知识目标、能力目标、素质目标）
3. 教学重点难点
4. 教学内容安排（详细列出主要知识点和讲解要点）
5. 实训练习与指导（设计具体的练习题和指导方案）
6. 教学方法与策略
7. 教学资源需求（教材、设备、软件等）
8. 课堂组织形式
9. 评估方式与标准
10. 课后拓展与作业

要求：
- 内容要具体详实，可直接用于教学
- 充分结合课程资料中的知识点和内容
- 教学安排要合理，循序渐进
- 实训练习要有针对性和实用性
- 语言专业规范，格式清晰
- 体现理论与实践相结合的教学理念

请用中文输出，结构化呈现。
"""
        
        messages = [
            {"role": "system", "content": "你是一位专业的教育专家和课程设计师，擅长制作详细的教学提纲。"},
            {"role": "user", "content": prompt}
        ]
        
        # 3. 调用DeepSeek API生成内容
        ai_content = chat_deepseek(messages)
        if not ai_content:
            raise ValueError("DeepSeek API返回空响应")
        
        # 4. 生成PDF文件（返回base64编码）
        pdf_base64, filename = _generate_pdf_content(
            title=f"《{course.name}》备课提纲",
            content=ai_content,
            course=course
        )
        
        return {
            "content": ai_content,
            "pdf_base64": pdf_base64,
            "filename": filename,
            "title": f"《{course.name}》备课提纲",
            "download_ready": True
        }
        
    except Exception as e:
        logger.error(f"生成备课提纲失败: {str(e)}")
        return {"error": f"生成失败: {str(e)}"}

def _get_selected_knowledge_content(course_id: int, selected_ids: List[int] = None) -> str:
    """获取选中的知识库内容作为AI生成参考
    
    Args:
        course_id (int): 课程ID
        selected_ids (List[int]): 选中的知识库ID列表
        
    Returns:
        str: 格式化的知识库内容
    """
    try:
        # 如果没有提供选中的ID，获取所有知识库内容
        if not selected_ids:
            all_knowledge = CourseService.get_knowledge_base_by_course(course_id=course_id)
        else:
            # 获取选中的知识库内容
            all_knowledge = KnowledgeBaseService.get_knowledge_by_ids(selected_ids)
        
        if not all_knowledge:
            return "没有选择任何课程资料，将基于基础模板生成内容。"
        
        # 格式化内容
        formatted_content = []
 
        for item in all_knowledge:
            # 判断内容类型：下载链接还是纯文本
            if item.content.startswith(('http://', 'https://', 'ftp://')):
                # 这是一个下载链接
                content_desc = f"文件链接: {item.content}"
                content_type = "可下载资源"
            else:
                # 这是纯文本内容
                content_preview = item.content[:500] + "..." if len(item.content) > 500 else item.content
                content_desc = f"文本内容: {content_preview}"
                content_type = "纯文本资源"
            
            formatted_item = f"""
【{item.title}】
类别: {item.category or '未分类'}
资源类型: {content_type}
内容: {content_desc}
创建时间: {item.created_at.strftime('%Y-%m-%d')}
---
"""
            formatted_content.append(formatted_item)
        
        result = f"以下是《课程ID:{course_id}》的相关教学资料（共{len(all_knowledge)}项）：\n\n"
        result += "\n".join(formatted_content)
        
        return result
        
    except Exception as e:
        logger.error(f"获取选中知识库内容失败: {str(e)}")
        return "获取课程资料失败，将基于基础模板生成内容。"

def _get_course_knowledge_content(course_id: int) -> str:
    """获取本课程的知识库内容作为AI生成参考
    
    Args:
        course_id (int): 课程ID
        
    Returns:
        str: 格式化的知识库内容
    """
    try:
        # 获取本课程的所有知识库内容
        all_knowledge = CourseService.get_knowledge_base_by_course(course_id=course_id)
        
        if not all_knowledge:
            return "暂无相关课程资料，请先上传课程教学资料到知识库。"
        
        # 格式化内容
        formatted_content = []
        
        for item in all_knowledge:
            # 判断内容类型：下载链接还是纯文本
            if item.content.startswith(('http://', 'https://', 'ftp://')):
                # 这是一个下载链接
                content_desc = f"文件链接: {item.content}"
                content_type = "可下载资源"
            else:
                # 这是纯文本内容
                content_preview = item.content[:500] + "..." if len(item.content) > 500 else item.content
                content_desc = f"文本内容: {content_preview}"
                content_type = "纯文本资源"
            
            formatted_item = f"""
【{item.title}】
类别: {item.category or '未分类'}
资源类型: {content_type}
内容: {content_desc}
创建时间: {item.created_at.strftime('%Y-%m-%d')}
---
"""
            formatted_content.append(formatted_item)
        
        result = f"以下是《课程ID:{course_id}》的相关教学资料：\n\n"
        result += "\n".join(formatted_content)
        
        return result
        
    except Exception as e:
        logger.error(f"获取课程知识库内容失败: {str(e)}")
        return "获取课程资料失败，将基于基础模板生成内容。"


def _generate_pdf_content(title: str, content: str, course: Course) -> tuple:
    """生成格式化的PDF文件并返回base64编码"""
    try:
        # 创建内存缓冲区
        buffer = io.BytesIO()
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{title}_{timestamp}.pdf"
        
        # 注册中文字体
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            from reportlab.pdfbase.ttfonts import TTFont
            
            # 尝试注册内置中文字体
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            chinese_font = 'STSong-Light'
        except:
            # 回退到系统字体
            try:
                # 尝试使用常见的简体中文字体
                font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'simhei.ttf')
                
                # 如果字体文件不存在，尝试系统字体
                if not os.path.exists(font_path):
                    # Windows 系统字体路径
                    font_path = 'C:/Windows/Fonts/simhei.ttf'
                    # Linux 系统字体路径
                    if not os.path.exists(font_path):
                        font_path = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
                
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                chinese_font = 'ChineseFont'
            except Exception as font_error:
                logger.error(f"字体注册失败: {str(font_error)}")
                chinese_font = 'Helvetica'  # 回退到英文字体
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            encoding='utf-8'
        )
        
        # 创建样式
        styles = getSampleStyleSheet()
        
        # 标题样式
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=22,
            spaceAfter=14,
            alignment=TA_CENTER,
            fontName=chinese_font
        )
        
        # 章节标题样式
        heading1_style = ParagraphStyle(
            'Heading1Style',
            parent=styles['Heading2'],
            fontSize=14,
            leading=20,
            spaceBefore=12,
            spaceAfter=8,
            fontName=chinese_font
        )
        
        # 章节副标题样式
        heading2_style = ParagraphStyle(
            'Heading2Style',
            parent=styles['Heading3'],
            fontSize=12,
            leading=18,
            spaceBefore=8,
            spaceAfter=6,
            fontName=chinese_font
        )
        
        # 正文样式
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=15,
            spaceAfter=6,
            fontName=chinese_font,
            wordWrap='CJK'
        )
        
        # 列表样式
        list_style = ParagraphStyle(
            'ListStyle',
            parent=body_style,
            leftIndent=12,
            bulletIndent=0,
            spaceBefore=4,
            spaceAfter=4
        )
        
        # 开始构建文档内容
        story = []
        
        # 添加主标题
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))
        
        # 添加课程信息
        course_info = f"课程名称: {course.name} | 课程代码: {course.code} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(course_info, body_style))
        story.append(Spacer(1, 24))
        
        # 解析Markdown内容并转换为PDF元素
        current_level = 0
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 处理章节标题
            if line.startswith('# '):
                story.append(Paragraph(line[2:], heading1_style))
                current_level = 1
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], heading2_style))
                current_level = 2
            elif line.startswith('### '):
                story.append(Paragraph(line[4:], heading2_style))
                current_level = 3
            # 处理列表项
            elif line.startswith('- ') or line.startswith('* '):
                story.append(Paragraph(line[2:], list_style))
            # 处理有序列表
            elif re.match(r'^\d+\.\s', line):
                story.append(Paragraph(line, list_style))
            # 处理普通段落
            else:
                # 如果是小标题后的内容，添加缩进
                if current_level > 1:
                    indented_style = ParagraphStyle(
                        'IndentedStyle',
                        parent=body_style,
                        leftIndent=12
                    )
                    story.append(Paragraph(line, indented_style))
                else:
                    story.append(Paragraph(line, body_style))
        
        # 构建PDF
        doc.build(story)
        
        # 获取PDF内容并转换为base64
        pdf_content = buffer.getvalue()
        buffer.close()
        
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        return pdf_base64, filename
        
    except Exception as e:
        logger.error(f"PDF生成失败: {str(e)}")
        # 如果PDF生成失败，生成文本文件的base64编码
        txt_content = f"{title}\n\n"
        txt_content += f"课程：{course.name}\n"
        txt_content += f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        txt_content += content
        
        txt_base64 = base64.b64encode(txt_content.encode('utf-8')).decode('utf-8')
        txt_filename = filename.replace('.pdf', '.txt')
        
        return txt_base64, txt_filename
    
def generate_teaching_summary(course_id: int, week: int, 
                           achievements: List[str], issues: List[str]) -> str:
    """生成教学总结
    
    Args:
        course_id (int): 课程ID
        week (int): 教学周次
        achievements (List[str]): 教学成果
        issues (List[str]): 存在问题
        
    Returns:
        str: 生成的教学总结
    """
    course = Course.get_by_id(course_id)
    if not course:
        return "错误：课程不存在"
    
    summary = f"【{course.name}】第{week}周教学总结\n\n"
    summary += "一、教学成果：\n"
    for i, ach in enumerate(achievements, 1):
        summary += f"{i}. {ach}\n"
    
    summary += "\n二、存在问题：\n"
    for i, issue in enumerate(issues, 1):
        summary += f"{i}. {issue}\n"
    
    summary += "\n三、改进措施：\n"
    summary += "1. 调整教学方法\n2. 增加辅导时间\n3. 优化教学资源\n"
    
    summary += f"\n总结时间：{datetime.now().strftime('%Y-%m-%d')}"
    return summary