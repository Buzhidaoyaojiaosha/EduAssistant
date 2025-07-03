from werkzeug.exceptions import HTTPException

from app.models.learning_data import (
    KnowledgePoint,
    AssignmentKnowledgePoint,
    KnowledgeBaseKnowledgePoint
)
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.knowledge_base import KnowledgeBase
from typing import List, Dict, Optional
from peewee import DoesNotExist
from app.react.tools_register import register_as_tool

# from app.ext import graph  # 已禁用图数据库相关
import pandas as pd
from py2neo import Graph, Node, Relationship
from app.models.course import Course


class KnowledgePointService:

    @register_as_tool(roles=["teacher"])
    @staticmethod
    def create_knowledge_point(name: str, course_id: int, description: str = None, parent_id: int = None) -> KnowledgePoint:
        """创建一个新的知识点。
        
        Args:
            name: 知识点名称。
            course_id: 所属课程ID。
            description: 知识点描述，可选。
            parent_id: 父知识点ID，可选。
            
        Returns:
            KnowledgePoint: 新创建的知识点对象。
            
        Raises:
            ValueError: 当课程不存在或父知识点不存在或不属于同一课程时抛出。
        """
        try:
            course = Course.get_by_id(course_id)
            
            # 检查父知识点是否存在
            parent = None
            if parent_id:
                try:
                    parent = KnowledgePoint.get_by_id(parent_id)
                    # 确保父知识点属于同一课程
                    if parent.course_id != course_id:
                        raise ValueError("父知识点必须属于同一课程")
                except DoesNotExist:
                    raise ValueError(f"父知识点ID {parent_id} 不存在")
            
            # 创建知识点
            knowledge_point = KnowledgePoint.create(
                name=name,
                description=description,
                course=course,
                parent=parent
            )
            
            return knowledge_point
        
        except DoesNotExist:
            raise ValueError(f"课程ID {course_id} 不存在")

    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def get_knowledge_point(knowledge_point_id: int) -> KnowledgePoint:
        """获取指定ID的知识点。
        
        Args:
            knowledge_point_id: 知识点ID。
            
        Returns:
            KnowledgePoint: 找到的知识点对象。
            
        Raises:
            ValueError: 当知识点不存在时抛出。
        """
        try:
            return KnowledgePoint.get_by_id(knowledge_point_id)
        except DoesNotExist:
            raise ValueError(f"知识点ID {knowledge_point_id} 不存在")

    @register_as_tool(roles=["student", "teacher"])
    @staticmethod
    def get_course_knowledge_points(course_id: int, include_tree: bool = False) -> List[KnowledgePoint]:
        """获取指定课程的所有知识点。
        
        Args:
            course_id: 课程ID。
            include_tree: 是否仅包含顶级知识点，默认为False。
            
        Returns:
            List[KnowledgePoint]: 知识点对象列表。
            
        Raises:
            ValueError: 当课程不存在时抛出。
        """
        try:
            Course.get_by_id(course_id)  # 验证课程是否存在
            
            if include_tree:
                # 仅获取顶级知识点
                top_level_points = KnowledgePoint.select().where(
                    (KnowledgePoint.course_id == course_id) & 
                    (KnowledgePoint.parent.is_null())
                )
                return list(top_level_points)
            else:
                # 获取所有知识点
                return list(KnowledgePoint.select().where(KnowledgePoint.course_id == course_id))
                
        except DoesNotExist:
            raise ValueError(f"课程ID {course_id} 不存在")

    @staticmethod
    def add_knowledge_points_to_assignment(
        assignment_id: int, 
        knowledge_point_ids: List[int],
        weights: Optional[Dict[int, float]] = None
    ) -> List[AssignmentKnowledgePoint]:
        """为作业关联知识点。
        
        Args:
            assignment_id: 作业ID。
            knowledge_point_ids: 知识点ID列表。
            weights: 知识点权重字典，键为知识点ID，值为权重，可选。
            
        Returns:
            List[AssignmentKnowledgePoint]: 新创建的关联对象列表。
            
        Raises:
            ValueError: 当作业不存在、知识点不存在或知识点不属于作业所在课程时抛出。
        """
        try:
            assignment = Assignment.get_by_id(assignment_id)
            course_id = assignment.course_id
            results = []
            
            for kp_id in knowledge_point_ids:
                try:
                    kp = KnowledgePoint.get_by_id(kp_id)
                    
                    # 确保知识点属于同一课程
                    if kp.course_id != course_id:
                        raise ValueError(f"知识点ID {kp_id} 不属于作业所在的课程")
                    
                    # 检查是否已经关联
                    try:
                        AssignmentKnowledgePoint.get(
                            assignment_id=assignment_id,
                            knowledge_point_id=kp_id
                        )
                        # 已存在关联，跳过
                        continue
                    except DoesNotExist:
                        # 不存在关联，创建新关联
                        weight = weights.get(kp_id, 1.0) if weights else 1.0
                        relation = AssignmentKnowledgePoint.create(
                            assignment=assignment,
                            knowledge_point=kp,
                            weight=weight
                        )
                        results.append(relation)
                
                except DoesNotExist:
                    raise ValueError(f"知识点ID {kp_id} 不存在")
            
            return results
            
        except DoesNotExist:
            raise ValueError(f"作业ID {assignment_id} 不存在")

    @staticmethod
    def add_knowledge_points_to_knowledge_base(
        knowledge_base_id: int, 
        knowledge_point_ids: List[int],
        weights: Optional[Dict[int, float]] = None
    ) -> List[KnowledgeBaseKnowledgePoint]:
        """为知识库条目关联知识点。
        
        Args:
            knowledge_base_id: 知识库条目ID。
            knowledge_point_ids: 知识点ID列表。
            weights: 知识点权重字典，键为知识点ID，值为权重，可选。
            
        Returns:
            List[KnowledgeBaseKnowledgePoint]: 新创建的关联对象列表。
            
        Raises:
            ValueError: 当知识库条目不存在、知识点不存在或知识点不属于知识库条目所在课程时抛出。
        """
        try:
            kb = KnowledgeBase.get_by_id(knowledge_base_id)
            course_id = kb.course_id if kb.course else None
            results = []
            
            for kp_id in knowledge_point_ids:
                try:
                    kp = KnowledgePoint.get_by_id(kp_id)
                    
                    # 如果知识库条目属于某个课程，确保知识点也属于同一课程
                    if course_id and kp.course_id != course_id:
                        raise ValueError(f"知识点ID {kp_id} 不属于知识库条目所在的课程")
                    
                    # 检查是否已经关联
                    try:
                        KnowledgeBaseKnowledgePoint.get(
                            knowledge_base_id=knowledge_base_id,
                            knowledge_point_id=kp_id
                        )
                        # 已存在关联，跳过
                        continue
                    except DoesNotExist:
                        # 不存在关联，创建新关联
                        weight = weights.get(kp_id, 1.0) if weights else 1.0
                        relation = KnowledgeBaseKnowledgePoint.create(
                            knowledge_base=kb,
                            knowledge_point=kp,
                            weight=weight
                        )
                        results.append(relation)
                
                except DoesNotExist:
                    raise ValueError(f"知识点ID {kp_id} 不存在")
            
            return results
            
        except DoesNotExist:
            raise ValueError(f"知识库条目ID {knowledge_base_id} 不存在")

    @staticmethod
    def remove_knowledge_point_from_assignment(assignment_id: int, knowledge_point_id: int) -> bool:
        """移除作业与知识点的关联。
        
        Args:
            assignment_id: 作业ID。
            knowledge_point_id: 知识点ID。
            
        Returns:
            bool: 如果成功删除关联返回True，如果关联不存在返回False。
        """
        try:
            relation = AssignmentKnowledgePoint.get(
                assignment_id=assignment_id,
                knowledge_point_id=knowledge_point_id
            )
            relation.delete_instance()
            return True
        except DoesNotExist:
            return False

    @staticmethod
    def remove_knowledge_point_from_knowledge_base(knowledge_base_id: int, knowledge_point_id: int) -> bool:
        """移除知识库条目与知识点的关联。
        
        Args:
            knowledge_base_id: 知识库条目ID。
            knowledge_point_id: 知识点ID。
            
        Returns:
            bool: 如果成功删除关联返回True，如果关联不存在返回False。
        """
        try:
            relation = KnowledgeBaseKnowledgePoint.get(
                knowledge_base_id=knowledge_base_id,
                knowledge_point_id=knowledge_point_id
            )
            
            relation.delete_instance()
            return True
        except DoesNotExist:
            return False

    @staticmethod
    def get_assignment_knowledge_points(assignment_id: int) -> List[Dict]:
        """获取作业关联的所有知识点。
        
        Args:
            assignment_id: 作业ID。
            
        Returns:
            List[Dict]: 包含知识点对象和权重的字典列表。
            
        Raises:
            ValueError: 当作业不存在时抛出。
        """
        try:
            Assignment.get_by_id(assignment_id)  # 验证作业是否存在
            
            query = (AssignmentKnowledgePoint
                     .select(AssignmentKnowledgePoint, KnowledgePoint)
                     .join(KnowledgePoint)
                     .where(AssignmentKnowledgePoint.assignment_id == assignment_id))
            
            results = []
            for relation in query:
                results.append({
                    'knowledge_point': relation.knowledge_point,
                    'weight': relation.weight
                })
            
            return results
            
        except DoesNotExist:
            raise ValueError(f"作业ID {assignment_id} 不存在")

    @staticmethod
    def get_knowledge_base_knowledge_points(knowledge_base_id: int) -> List[Dict]:
        """获取知识库条目关联的所有知识点。
        
        Args:
            knowledge_base_id: 知识库条目ID。
            
        Returns:
            List[Dict]: 包含知识点对象和权重的字典列表。
            
        Raises:
            ValueError: 当知识库条目不存在时抛出。
        """
        try:
            KnowledgeBase.get_by_id(knowledge_base_id)  # 验证知识库条目是否存在
            
            query = (KnowledgeBaseKnowledgePoint
                     .select(KnowledgeBaseKnowledgePoint, KnowledgePoint)
                     .join(KnowledgePoint)
                     .where(KnowledgeBaseKnowledgePoint.knowledge_base_id == knowledge_base_id))
            
            results = []
            for relation in query:
                results.append({
                    'knowledge_point': relation.knowledge_point,
                    'weight': relation.weight
                })
            
            return results
            
        except DoesNotExist:
            raise ValueError(f"知识库条目ID {knowledge_base_id} 不存在")

    @register_as_tool(roles=["teacher"])
    @staticmethod
    def import_excel_to_knowledge_points(file_path: str, course_id: int):
        """
        将 Excel 中的知识点导入PostgreSQL数据库(基于父子层级结构)。

        参数:
            file_path: Excel文件流。
            course_id: 所属课程的 ID。
        """

        # 读取表格
        df = pd.read_excel(file_path, header=None)

        LEVEL_COLS = [0, 1, 2]  # 知识点列：0 - 一级，1 - 二级，2 - 三级
        id_cache = {}  # 缓存已创建知识点：{name: id}
        latest_level_1_id = None
        latest_level_2_id = None

        for _, row in df.iterrows():
            name_lvl1 = str(row[0]).strip() if pd.notna(row[0]) else None
            name_lvl2 = str(row[1]).strip() if pd.notna(row[1]) else None
            name_lvl3 = str(row[2]).strip() if pd.notna(row[2]) else None
            
            description_parts = []
            for col in [13, 14]:
                if pd.notna(row[col]):
                    description_parts.append(str(row[col]).strip())
            description = ';'.join(description_parts) if description_parts else None


            try:
                if name_lvl1:
                    
                    # 检查名称是否已存在
                    if name_lvl1 in id_cache:
                        latest_level_1_id = id_cache[name_lvl1]
                        latest_level_2_id = None
                        continue
                    
                    # 创建一级知识点（无父）
                    kp1 = KnowledgePointService.create_knowledge_point(name=name_lvl1, course_id=course_id, description=None, parent_id=None)
                    id_cache[name_lvl1] = kp1.get_id()
                    latest_level_1_id = kp1.get_id()
                    latest_level_2_id = None  # 清空二级缓存

                elif name_lvl2 and latest_level_1_id:
                    
                    # 检查二级名称是否已存在
                    if name_lvl2 in id_cache:
                        latest_level_2_id = id_cache[name_lvl2]
                        continue
                    
                    
                    # 创建二级知识点，父为最近一级
                    kp2 = KnowledgePointService.create_knowledge_point(name=name_lvl2, course_id=course_id, description=None,
                                                 parent_id=latest_level_1_id)
                    id_cache[name_lvl2] = kp2.get_id()
                    latest_level_2_id = kp2.get_id()

                elif name_lvl3 and latest_level_2_id:
                    
                     # 检查三级名称是否已存在
                    if name_lvl3 in id_cache:
                        continue
                    
                    # 创建三级知识点，父为最近二级
                    kp3 = KnowledgePointService.create_knowledge_point(name=name_lvl3, course_id=course_id, description=description,
                                                 parent_id=latest_level_2_id)
                    id_cache[name_lvl3] = kp3.get_id()

            except ValueError as e:
                print(f"[跳过] 创建失败：{e}")
                continue

        print(f"✅ 课程 {course_id} 的知识点导入 PostgreSQL 完成，共导入 {len(id_cache)} 个节点。")


    @staticmethod
    def excel_to_knowledge_point_graph(file, course_id,id_cache):
        '''
        将Excel文件中的知识点导入到Neo4j图数据库中。


        Args:
        file: Excel文件流。
        course_id: 所属课程的ID。
        '''
        
        LEVEL_COLS = [0, 1, 2]  # 三级知识点列
        DESCRIPTION_COL = 14  # 描述列
        PREREQ_COL = 8  # 前置知识点列
        POSTREQ_COL = 9  # 后置知识点列
        RELATED_COL = 10  # 关联知识点列

        #获取课程名称
        course_name = Course.get_by_id(course_id).name

        # 清空旧数据（当前课程下的知识点）
        graph.run("""
                MATCH (c:Course {id: $course_id})<-[:BELONGS_TO]-(k:Knowledge)
                DETACH DELETE k,c
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
        latest_level_1 = None
        latest_level_2 = None

        # 用于批量处理
        nodes = set()
        rel_belongs = set()
        rel_sub = set()
        rel_precedes = set()
        rel_related = set()

        def cache_node(name, level=None, description=None):
            name = str(name).strip()
            if not name:
                return None
            nodes.add((name, level, description))
            return name

        for _, row in df.iterrows():
            level_1 = row[0] if pd.notna(row[0]) else None
            level_2 = row[1] if pd.notna(row[1]) else None
            level_3 = row[2] if pd.notna(row[2]) else None

            description = str(row[DESCRIPTION_COL]).strip() if pd.notna(row[DESCRIPTION_COL]) else None

            if level_1:
                latest_level_1 = str(level_1).strip()
                latest_level_2 = None
                cache_node(latest_level_1, 1)
                rel_belongs.add((latest_level_1, course_id))

            elif level_2:
                latest_level_2 = str(level_2).strip()
                cache_node(latest_level_2, 2)
                if latest_level_1:
                    rel_sub.add((latest_level_2, latest_level_1))

            elif level_3:
                level_3_name = str(level_3).strip()
                cache_node(level_3_name, 3, description)
                if latest_level_2:
                    rel_sub.add((level_3_name, latest_level_2))

                # 当前行的知识点就是第3层
                current_node = level_3_name

                # 前置知识点
                if pd.notna(row[PREREQ_COL]):
                    for item in str(row[PREREQ_COL]).split(';'):
                        item = item.strip()
                        if item:
                            cache_node(item)
                            rel_precedes.add((item, current_node))

                # 后置知识点
                if pd.notna(row[POSTREQ_COL]):
                    for item in str(row[POSTREQ_COL]).split(';'):
                        item = item.strip()
                        if item:
                            cache_node(item)
                            rel_precedes.add((current_node, item))

                # 关联知识点
                if pd.notna(row[RELATED_COL]):
                    for item in str(row[RELATED_COL]).split(';'):
                        item = item.strip()
                        if item:
                            cache_node(item)
                            rel_related.add((current_node, item))

        # 批量写入数据库
        tx = graph.begin()

        # 创建所有 Knowledge 节点，添加pg_id属性
        tx.run("""
                UNWIND $nodes AS n
                MERGE (k:Knowledge {name: n.name})
                SET k.level = coalesce(n.level, k.level),
                    k.description = coalesce(n.description, k.description),
                    k.pg_id = $id_cache[n.name]  
            """, nodes=[{"name": n[0], "level": n[1], "description": n[2]} for n in nodes], id_cache=id_cache)
        
        # 创建 BELONGS_TO 关系
        tx.run("""
                UNWIND $rels AS r
                MATCH (k:Knowledge {name: r.knowledge})
                MATCH (c:Course {id: r.course})
                MERGE (k)-[:BELONGS_TO]->(c)
            """, rels=[{"knowledge": r[0], "course": r[1]} for r in rel_belongs])

        # 创建 SUB_KNOWLEDGE_OF 关系
        tx.run("""
                UNWIND $rels AS r
                MATCH (a:Knowledge {name: r.child})
                MATCH (b:Knowledge {name: r.parent})
                MERGE (a)-[:SUB_KNOWLEDGE_OF]->(b)
            """, rels=[{"child": r[0], "parent": r[1]} for r in rel_sub])

        # 创建 PRECEDES 关系
        tx.run("""
                UNWIND $rels AS r
                MATCH (a:Knowledge {name: r.from})
                MATCH (b:Knowledge {name: r.to})
                MERGE (a)-[:PRECEDES]->(b)
            """, rels=[{"from": r[0], "to": r[1]} for r in rel_precedes])

        # 创建 RELATED_TO 关系
        tx.run("""
                UNWIND $rels AS r
                MATCH (a:Knowledge {name: r.from})
                MATCH (b:Knowledge {name: r.to})
                MERGE (a)-[:RELATED_TO]->(b)
            """, rels=[{"from": r[0], "to": r[1]} for r in rel_related])

        tx.commit()
    
          
    @staticmethod
    def add_knowledge_to_graph(name: str, course_id: int, description: str = None, parent_id: int = None) -> KnowledgePoint:

        '''
        把手动加的知识点添加到neo4j图数据库和postgreSQL数据库。
        Args:
        name: 知识点名称。
        course_id: 所属课程的ID。
        description: 知识点描述。
        parent_id: 父知识点ID。

        Returns:
        KnowledgePoint: 创建的知识点对象。

        Raises:
        ValueError: 如果课程ID不存在。
        ValueError: 如果父知识点ID不存在。
        ValueError: 如果父知识点必须属于同一课程。
        '''

        try:
            course = Course.get_by_id(course_id)

            # 检查父知识点是否存在
            parent = None
            if parent_id:
                try:
                    parent = KnowledgePoint.get_by_id(parent_id)
                    if parent.course_id != course_id:
                        raise ValueError("父知识点必须属于同一课程")
                except DoesNotExist:
                    raise ValueError(f"父知识点ID {parent_id} 不存在")

            # === 创建 PostgreSQL 中的知识点 ===
            knowledge_point = KnowledgePoint.create(
                name=name,
                description=description,
                course=course,
                parent=parent
            )

            # === 同步到 Neo4j ===
            name = name.strip()
            description = description.strip() if description else None

            # 创建知识点节点
            graph.run("""
                    MERGE (k:Knowledge {name: $name})
                    SET k.description = coalesce($description, k.description)
                """, name=name, description=description)

            if parent:
                # 检查父节点是否在图中存在
                parent_exists = graph.evaluate("MATCH (p:Knowledge {name: $name}) RETURN p", name=parent.name.strip())
                if parent_exists:
                    # 父节点存在，建立父子关系
                    graph.run("""
                            MATCH (p:Knowledge {name: $parent_name})
                            MATCH (k:Knowledge {name: $child_name})
                            MERGE (k)-[:SUB_KNOWLEDGE_OF]->(p)
                        """, parent_name=parent.name.strip(), child_name=name)
                else:
                    print(f"[跳过图更新] 父节点 '{parent.name}' 不在图中，未建立父子关系")
            else:
                # 无父节点，建立属于课程的关系
                graph.run("""
                        MERGE (c:Course {id: $course_id})
                        SET c.name = $course_name
                    """, course_id=course.id, course_name=course.name)

                graph.run("""
                        MATCH (k:Knowledge {name: $name})
                        MATCH (c:Course {id: $course_id})
                        MERGE (k)-[:BELONGS_TO]->(c)
                    """, name=name, course_id=course.id)

            return knowledge_point

        except DoesNotExist:
            raise ValueError(f"课程ID {course_id} 不存在")


    @staticmethod
    def update_knowledge_point_node(kp_id: int, name: str, description: str, parent_id: int, course_id: int):
        # 删除原来的 Knowledge 节点（按 id 匹配）并重建
        graph.run("""
                MATCH (k:Knowledge {id: $id}) DETACH DELETE k
            """, id=kp_id)

        # 重建 Knowledge 节点
        graph.run("""
                MERGE (k:Knowledge {id: $id})
                SET k.name = $name,
                    k.description = $description
            """, id=kp_id, name=name, description=description or "")

        # 建立 BELONGS_TO 关系（如果没有父节点）
        if parent_id is None:
            graph.run("""
                    MATCH (k:Knowledge {id: $id})
                    MATCH (c:Course {id: $course_id})
                    MERGE (k)-[:BELONGS_TO]->(c)
                """, id=kp_id, course_id=course_id)
        else:
            # 建立 SUB_KNOWLEDGE_OF 关系（父子关系）
            graph.run("""
                    MATCH (k:Knowledge {id: $id})
                    MATCH (p:Knowledge {id: $parent_id})
                    MERGE (k)-[:SUB_KNOWLEDGE_OF]->(p)
                """, id=kp_id, parent_id=parent_id)

    @staticmethod
    def delete_knowledge_point_node_from_graph(kp_id:int):
        graph.run("""
            MATCH (k:Knowledge {id: $id})
            DETACH DELETE k
        """, id=kp_id)