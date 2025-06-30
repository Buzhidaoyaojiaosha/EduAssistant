from app.ext import graph
import pandas as pd
from py2neo import Graph, Node, Relationship
from app.models.course import Course
import app.services.knowledge_point_service

class GraphService:


    @staticmethod
    def excel_to_knowledge_point_graph(file, course_id):

        course_name = Course.get_by_id(course_id)

        LEVEL_COLS = [0, 1, 2]  # 三级知识点列
        DESCRIPTION_COL = 14  # 描述列
        PREREQ_COL = 8  # 前置知识点列
        POSTREQ_COL = 9  # 后置知识点列
        RELATED_COL = 10  # 关联知识点列

        # 清空旧数据（当前课程下的知识点）
        graph.run("""
            MATCH (c:Course {id: $course_id})<-[:BELONGS_TO]-(k:Knowledge)
            DETACH DELETE k
        """, course_id=course_id)

        df = pd.read_excel(file, header=None)

        # 创建或获取课程节点
        course_exists = graph.run("""
            MATCH (c:Course {id: $course_id}) RETURN c
        """, course_id=course_id).data()

        if course_exists:
            course_node = course_exists[0]['c']
            print(f"课程 [{course_id}] 已存在，使用原有节点")
        else:
            course_node = Node("Course", id=course_id, name=course_name or course_id)
            graph.create(course_node)
            print(f"课程 [{course_id}] 不存在，已新建")

        node_cache = {}
        current_hierarchy = {1: None, 2: None, 3: None}  # 当前层级状态
        tx = graph.begin()

        def get_or_create_node(name, level=None, description=None):
            name = str(name).strip()
            if not name:
                return None
            if name not in node_cache:
                node = Node("Knowledge", name=name)
                if level is not None:
                    node["level"] = int(level)
                if description and pd.notna(description):
                    node["description"] = str(description).strip()
                tx.merge(node, "Knowledge", "name")
                node_cache[name] = node
            return node_cache[name]

        for _, row in df.iterrows():
            # 层级知识点处理
            for col in LEVEL_COLS:
                name = row[col]
                if pd.notna(name):
                    level = col + 1
                    name = str(name).strip()
                    if level == 1:
                        current_hierarchy = {1: name, 2: None, 3: None}
                    elif level == 2:
                        current_hierarchy[2] = name
                        current_hierarchy[3] = None
                    elif level == 3:
                        current_hierarchy[3] = name

                    description = row[DESCRIPTION_COL] if col == LEVEL_COLS[-1] and pd.notna(
                        row[DESCRIPTION_COL]) else None
                    node = get_or_create_node(name, level, description)

                    # 父子关系
                    if level > 1 and current_hierarchy[level - 1]:
                        parent = get_or_create_node(current_hierarchy[level - 1])
                        if node and parent:
                            tx.merge(Relationship(node, "SUB_KNOWLEDGE_OF", parent))

                    # 顶层绑定课程
                    if level == 1:
                        tx.merge(Relationship(node, "BELONGS_TO", course_node))

            # 识别最底层知识点
            current_node = None
            if current_hierarchy[3]:
                current_node = get_or_create_node(current_hierarchy[3])
            elif current_hierarchy[2]:
                current_node = get_or_create_node(current_hierarchy[2])

            if current_node:
                # 前置知识点
                if pd.notna(row[PREREQ_COL]):
                    for pre in str(row[PREREQ_COL]).split(';'):
                        pre = pre.strip()
                        if pre:
                            pre_node = get_or_create_node(pre)
                            if pre_node:
                                tx.merge(Relationship(pre_node, "PRECEDES", current_node))

                # 后置知识点
                if pd.notna(row[POSTREQ_COL]):
                    for suc in str(row[POSTREQ_COL]).split(';'):
                        suc = suc.strip()
                        if suc:
                            suc_node = get_or_create_node(suc)
                            if suc_node:
                                tx.merge(Relationship(current_node, "PRECEDES", suc_node))

                # 关联知识点
                if pd.notna(row[RELATED_COL]):
                    for rel in str(row[RELATED_COL]).split(';'):
                        rel = rel.strip()
                        if rel:
                            rel_node = get_or_create_node(rel)
                            if rel_node:
                                tx.merge(Relationship(current_node, "RELATED_TO", rel_node))

        tx.commit()
        print(f"课程 [{course_id}] 的知识图谱构建完成，共导入 {len(node_cache)} 个知识点。")

    @staticmethod
    def view_knowledge_graph(course_id):
        # 查询当前课程下的所有知识点节点
        query = """
        MATCH (c:Course {id: $course_id})<-[:BELONGS_TO]-(k:Knowledge)
        OPTIONAL MATCH (k)-[r]-(other)
        RETURN k, collect(r), collect(other)
        """
        result = graph.run(query, course_id=course_id).data()
        
        # 转换结果为适合前端展示的格式（这里以简单字典为例）
        pass
