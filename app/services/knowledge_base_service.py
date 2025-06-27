from app.models.knowledge_base import KnowledgeBase
from app.ext import knowledge_base_collection
import uuid
import oss2
from pathlib import Path
import os
from urllib.parse import urlparse
class KnowledgeBaseService:
    """知识库服务, 处理FAQ和知识内容的存储、检索。
    
    该服务提供知识库相关功能，包括添加知识条目、向量化存储和检索等。
    使用ChromaDB进行向量存储和语义检索。
    """
    
    @staticmethod
    def add_knowledge(title, type,content, course_id=None, category=None, tags=None):
        """添加知识条目到知识库。
        
        Args:
            title (str): 标题
            type(str): 类型（1:纯文字，2:pdf,3:pptx,4:其他）
            content (str): 内容
            course_id (int, optional): 关联的课程ID
            category (str, optional): 分类
            tags (list, optional): 标签列表
            
        Returns:
            KnowledgeBase: 创建的知识条目对象
        """
        # 创建数据库记录
        knowledge = KnowledgeBase.create(
            title=title,
            type=type,
            content=content,
            course_id=course_id,
            category=category,
            tags=tags
        )
        
        # 生成唯一ID
        vector_id = str(uuid.uuid4())
        knowledge.vector_id = vector_id
        knowledge.save()
        
        # 添加到向量数据库
        knowledge_base_collection.add(
            ids=[vector_id],
            documents=[content],
            metadatas=[{
                "id": knowledge.id,
                "title": title,
                "category": category or "",
                "course_id": course_id or 0,
                "tags": ",".join(tags) if tags else ""
            }]
        )
        
        return knowledge
    
    @staticmethod
    def search_knowledge(query, course_id=None, limit=5, keyword_weight=0.3):
        """
        升级版知识库搜索：结合语义搜索和关键字全文搜索
        
        Args:
            query (str): 查询文本
            course_id (int, optional): 课程ID，用于筛选指定课程的知识
            limit (int): 返回结果数量限制
            keyword_weight (float): 关键字搜索结果的权重系数 (0-1之间)
            
        Returns:
            list: 匹配结果列表，按综合相关性排序
        """
        # 1. 执行语义搜索（向量搜索）
        vector_results = []
        vector_search = knowledge_base_collection.query(
            query_texts=[query],
            n_results=limit * 3  # 获取更多结果用于后续融合
        )
        
        if len(vector_search["ids"]) > 0:
            for i, vector_id in enumerate(vector_search["ids"][0]):
                metadata = vector_search["metadatas"][0][i]
                document = vector_search["documents"][0][i]
                distance = vector_search["distances"][0][i] if "distances" in vector_search else None
                
                # 获取完整记录
                db_record = KnowledgeBase.get_or_none(KnowledgeBase.vector_id == vector_id)
                if not db_record:
                    continue
                    
                vector_results.append({
                    "id": metadata["id"],
                    "vector_id": vector_id,
                    "title": metadata["title"],
                    "type": db_record.type,
                    "content": document,
                    "vector_distance": distance,
                    "category": metadata["category"],
                    "course_id": metadata["course_id"],
                    "tags": metadata["tags"].split(",") if metadata["tags"] else [],
                    "full_record": db_record,
                    "score": 1 - (distance if distance is not None else 1)  # 距离转换为相似度分数
                })
             

        # 2. 执行关键字全文搜索（基于标题和内容）
        keyword_results = []
        # 使用Peewee的SQL函数进行关键字匹配
        keyword_query = KnowledgeBase.select().where(
            (KnowledgeBase.title.contains(query)) |
            (KnowledgeBase.content.contains(query))
        )
        
        if course_id is not None:
            keyword_query = keyword_query.where(KnowledgeBase.course_id == course_id)
            
        keyword_query = keyword_query.limit(limit * 3)  # 获取更多结果用于后续融合
        
        for knowledge in keyword_query:
            # 计算关键字匹配分数（简单实现：匹配次数越多分数越高）
            title_matches = knowledge.title.lower().count(query.lower())
            content_matches = knowledge.content.lower().count(query.lower())
            keyword_score = min(1.0, 0.1 * title_matches + 0.01 * content_matches)
            
            keyword_results.append({
                "id": knowledge.id,
                "vector_id": knowledge.vector_id,
                "title": knowledge.title,
                "type": knowledge.type,
                "content": knowledge.content,
                "vector_distance": None,
                "category": knowledge.category,
                "course_id": knowledge.course_id,
                "tags": knowledge.tags,
                "full_record": knowledge,
                "score": keyword_score
            })

        # 3. 融合两种搜索结果
        all_results = {}
        
        # 添加向量搜索结果
        for result in vector_results:
            all_results[result["id"]] = {
                **result,
                "combined_score": result["score"]
            }
        
        # 添加关键字搜索结果并融合分数
        for result in keyword_results:
            if result["id"] in all_results:
                # 如果结果已在向量搜索中，则融合分数
                existing = all_results[result["id"]]
                combined_score = (1 - keyword_weight) * existing["score"] + keyword_weight * result["score"]
                all_results[result["id"]]["combined_score"] = combined_score
            else:
                # 新结果，只使用关键字分数
                all_results[result["id"]] = {
                    **result,
                    "combined_score": result["score"] * keyword_weight
                }

        # 4. 按融合分数排序并限制结果数量
        sorted_results = sorted(
            all_results.values(), 
            key=lambda x: x["combined_score"], 
            reverse=True
        )[:limit]
        
        # 5. 添加额外的元数据并返回
        final_results = []
        for result in sorted_results:
            # 计算匹配类型标签
            match_types = []
            if result.get("vector_distance") is not None:
                match_types.append("语义匹配")
                
            if "score" in result and result["score"] > 0:
                match_types.append("关键词匹配")
                
            final_results.append({
                **result,
                "match_types": match_types,
                "combined_score": round(result["combined_score"], 4)  # 保留4位小数
            })
        
        return final_results
    
    @staticmethod
    def delete_knowledge(knowledge_id):
        """删除知识条目。
        
        Args:
            knowledge_id (int): 知识条目ID
            
        Returns:
            bool: 操作是否成功
        """
        knowledge = KnowledgeBase.get_or_none(id=knowledge_id)
        if not knowledge or not knowledge.vector_id:
            return False
            
        # 从向量数据库中删除
        try:
            knowledge_base_collection.delete(ids=[knowledge.vector_id])
        except:
            pass  # 即使向量删除失败也继续删除数据库记录
            
        # 删除数据库记录
        knowledge.delete_instance()
        return True
    
    @staticmethod
    def update_knowledge(knowledge_id, title=None, content=None, 
                        category=None, tags=None):
        """更新知识条目。
        
        Args:
            knowledge_id (int): 知识条目ID
            title (str, optional): 新标题
            content (str, optional): 新内容
            category (str, optional): 新分类
            tags (list, optional): 新标签列表
            
        Returns:
            KnowledgeBase: 更新后的知识条目对象
            
        Raises:
            ValueError: 如果找不到指定的知识条目
        """
        knowledge = KnowledgeBase.get_or_none(id=knowledge_id)
        if not knowledge:
            raise ValueError(f"知识条目ID {knowledge_id} 不存在")
            
        # 更新数据库记录
        if title is not None:
            knowledge.title = title
        if content is not None:
            knowledge.content = content
        if category is not None:
            knowledge.category = category
        if tags is not None:
            knowledge.tags = tags
            
        knowledge.save()
        
        # 如果内容或元数据变化，更新向量数据库
        if content is not None or title is not None or category is not None or tags is not None:
            if knowledge.vector_id:
                try:
                    # 删除旧向量
                    knowledge_base_collection.delete(ids=[knowledge.vector_id])
                except:
                    pass
                    
                # 添加新向量
                knowledge_base_collection.add(
                    ids=[knowledge.vector_id],
                    documents=[knowledge.content],
                    metadatas=[{
                        "id": knowledge.id,
                        "title": knowledge.title,
                        "category": knowledge.category or "",
                        "course_id": knowledge.course_id or 0,
                        "tags": ",".join(knowledge.tags) if knowledge.tags else ""
                    }]
                )
                
        return knowledge

    @staticmethod
    def upload_file_to_oss(local_file_path):
        """上传文件到OSS并返回可直接显示中文的URL"""
      
        
        # 初始化OSS
        auth = oss2.Auth(
            os.getenv('OSS_ACCESS_KEY_ID'),
            os.getenv('OSS_ACCESS_KEY_SECRET')
        )

        """上传文件并设置为公共读"""
        endpoint = os.getenv('OSS_ENDPOINT')
        bucket_name = os.getenv('OSS_BUCKET_NAME')
        if not os.path.isfile(local_file_path):
            raise FileNotFoundError(f"文件不存在: {local_file_path}")

        bucket = oss2.Bucket(auth, f'https://{endpoint}', bucket_name)
        object_name = Path(local_file_path).name
        print(f"开始上传文件:local_file_path {local_file_path} 到 OSS 存储桶:bucket_name {bucket_name}  object_name {object_name}")
        try:
            # 上传文件
            result = bucket.put_object_from_file(
                object_name,
                local_file_path,
                headers={'Content-Type': 'application/pdf'}
            )
            
            if result.status == 200:
                # 只设置这个文件为公共读
                bucket.put_object_acl(object_name, oss2.OBJECT_ACL_PUBLIC_READ)
                file_url = f"https://{bucket_name}.{endpoint}/{object_name}"
                print(f"文件上传成功: {file_url}")
                return file_url
            else:
                raise Exception(f"上传失败，状态码: {result.status}")
        except Exception as e:
            raise Exception(f"上传出错: {str(e)}")
        
    @staticmethod
    def delete_file_from_oss(file_url):
        """从OSS中删除文件"""
        try:
            # 从URL中提取对象名
            parsed_url = urlparse(file_url)
            object_name = parsed_url.path.lstrip('/')
            
            # 初始化OSS
            auth = oss2.Auth(
                os.getenv('OSS_ACCESS_KEY_ID'),
                os.getenv('OSS_ACCESS_KEY_SECRET')
            )
            endpoint = os.getenv('OSS_ENDPOINT')
            bucket_name = os.getenv('OSS_BUCKET_NAME')
            
            bucket = oss2.Bucket(auth, f'https://{endpoint}', bucket_name)
            
            # 删除文件
            result = bucket.delete_object(object_name)
            
            if result.status == 204:
                print(f"文件删除成功: {object_name}")
                return True
            else:
                print(f"文件删除失败，状态码: {result.status}")
                return False
                
        except Exception as e:
            print(f"删除文件出错: {str(e)}")
            return False