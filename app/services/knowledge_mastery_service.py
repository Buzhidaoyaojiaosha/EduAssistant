import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Tuple, Optional
import json
from datetime import datetime
from peewee import DoesNotExist, fn
import math

from app.models.learning_data import StudentKnowledgePoint, AssignmentKnowledgePoint, KnowledgePoint
from app.models.assignment import StudentAssignment, Assignment
from app.models.course import Course, StudentCourse
from app.models.user import User
from app.services.knowledge_point_service import KnowledgePointService


class NeuralCDMDataset(Dataset):
    """NeuralCDM 训练数据集"""
    
    def __init__(self, student_ids: List[int], assignment_ids: List[int], 
                 knowledge_point_ids: List[int], scores: List[float], 
                 assignment_knowledge_maps: Dict[int, List[int]]):
        self.student_ids = student_ids
        self.assignment_ids = assignment_ids
        self.knowledge_point_ids = knowledge_point_ids
        self.scores = scores
        self.assignment_knowledge_maps = assignment_knowledge_maps
        
        # 创建ID映射
        self.student_id_to_idx = {sid: idx for idx, sid in enumerate(set(student_ids))}
        self.assignment_id_to_idx = {aid: idx for idx, aid in enumerate(set(assignment_ids))}
        self.knowledge_id_to_idx = {kid: idx for idx, kid in enumerate(set(knowledge_point_ids))}
        
        self.num_students = len(self.student_id_to_idx)
        self.num_assignments = len(self.assignment_id_to_idx)
        self.num_knowledge_points = len(self.knowledge_id_to_idx)
    
    def __len__(self):
        return len(self.scores)
    
    def __getitem__(self, idx):
        student_id = self.student_ids[idx]
        assignment_id = self.assignment_ids[idx]
        score = self.scores[idx]
        
        # 获取作业关联的知识点
        knowledge_points = self.assignment_knowledge_maps.get(assignment_id, [])
        
        return {
            'student_idx': self.student_id_to_idx[student_id],
            'assignment_idx': self.assignment_id_to_idx[assignment_id],
            'knowledge_points': knowledge_points,
            'score': score
        }


class AttentionLayer(nn.Module):
    """注意力机制层"""
    
    def __init__(self, knowledge_dim: int, hidden_dim: int = 64):
        super(AttentionLayer, self).__init__()
        self.knowledge_dim = knowledge_dim
        self.hidden_dim = hidden_dim
        
        # 注意力权重计算
        self.attention = nn.Sequential(
            nn.Linear(knowledge_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
            nn.Softmax(dim=1)
        )
    
    def forward(self, knowledge_vectors, knowledge_mask):
        """
        Args:
            knowledge_vectors: [batch_size, max_knowledge_points, knowledge_dim]
            knowledge_mask: [batch_size, max_knowledge_points]
        """
        # 计算注意力权重
        attention_weights = self.attention(knowledge_vectors)  # [batch_size, max_knowledge_points, 1]
        
        # 应用mask
        attention_weights = attention_weights * knowledge_mask.unsqueeze(-1)
        
        # 加权求和
        weighted_sum = torch.sum(attention_weights * knowledge_vectors, dim=1)  # [batch_size, knowledge_dim]
        
        return weighted_sum, attention_weights.squeeze(-1)


class NeuralCDMModel(nn.Module):
    """NeuralCDM 模型"""
    
    def __init__(self, num_students: int, num_knowledge_points: int, 
                 knowledge_dim: int = 32, hidden_dim: int = 64, dropout: float = 0.2):
        super(NeuralCDMModel, self).__init__()
        
        self.num_students = num_students
        self.num_knowledge_points = num_knowledge_points
        self.knowledge_dim = knowledge_dim
        
        # 学生知识点掌握度嵌入
        self.student_knowledge_embeddings = nn.Parameter(
            torch.randn(num_students, num_knowledge_points, knowledge_dim)
        )
        
        # 注意力层
        self.attention = AttentionLayer(knowledge_dim, hidden_dim)
        
        # MLP预测层
        self.mlp = nn.Sequential(
            nn.Linear(knowledge_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()  # 输出0-1之间的得分
        )
        
        # 初始化参数
        self._init_weights()
    
    def _init_weights(self):
        """初始化模型权重"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    def forward(self, student_indices, assignment_knowledge_points, max_knowledge_points=10):
        """
        Args:
            student_indices: [batch_size]
            assignment_knowledge_points: List[List[int]] - 每个作业的知识点列表
            max_knowledge_points: 最大知识点数量
        """
        batch_size = len(student_indices)
        
        # 获取学生的知识点掌握度向量
        student_embeddings = self.student_knowledge_embeddings[student_indices]  # [batch_size, num_knowledge_points, knowledge_dim]
        
        # 构建批次的知识点向量和mask
        knowledge_vectors = torch.zeros(batch_size, max_knowledge_points, self.knowledge_dim)
        knowledge_mask = torch.zeros(batch_size, max_knowledge_points)
        
        for i, knowledge_points in enumerate(assignment_knowledge_points):
            for j, kp_idx in enumerate(knowledge_points[:max_knowledge_points]):
                knowledge_vectors[i, j] = student_embeddings[i, kp_idx]
                knowledge_mask[i, j] = 1.0
        
        # 应用注意力机制
        weighted_knowledge, attention_weights = self.attention(knowledge_vectors, knowledge_mask)
        
        # MLP预测得分
        predicted_scores = self.mlp(weighted_knowledge).squeeze(-1)
        
        return predicted_scores, attention_weights


class NeuralCDMService:
    """NeuralCDM 知识点掌握度计算服务"""
    
    def __init__(self, device: str = 'cpu'):
        self.device = device
        self.model = None
        self.student_id_to_idx = {}
        self.knowledge_id_to_idx = {}
        self.idx_to_student_id = {}
        self.idx_to_knowledge_id = {}
    
    def prepare_training_data(self, course_id: int) -> Tuple[NeuralCDMDataset, Dict]:
        """
        准备训练数据
        
        Args:
            course_id: 课程ID
            
        Returns:
            Tuple[NeuralCDMDataset, Dict]: 数据集和元数据
        """
        # 获取课程所有学生
        enrollments = StudentCourse.select().where(StudentCourse.course_id == course_id)
        students = [enrollment.student for enrollment in enrollments]
        
        # 获取课程所有知识点
        knowledge_points = KnowledgePointService.get_course_knowledge_points(course_id)
        
        # 获取课程所有作业
        assignments = Assignment.select().where(Assignment.course_id == course_id)
        
        # 构建训练数据
        student_ids = []
        assignment_ids = []
        knowledge_point_ids = []
        scores = []
        assignment_knowledge_maps = {}
        
        for student in students:
            for assignment in assignments:
                # 获取学生作业得分
                try:
                    student_assignment = StudentAssignment.get(
                        StudentAssignment.student_id == student.id,
                        StudentAssignment.assignment_id == assignment.id
                    )
                    
                    if student_assignment.final_score is not None and student_assignment.status == 2:
                        # 获取作业关联的知识点
                        assignment_knowledge = KnowledgePointService.get_assignment_knowledge_points(assignment.id)
                        
                        if assignment_knowledge:
                            # 记录数据
                            student_ids.append(student.id)
                            assignment_ids.append(assignment.id)
                            knowledge_point_ids.extend([kp['knowledge_point'].id for kp in assignment_knowledge])
                            scores.append(student_assignment.final_score / student_assignment.total_score)
                            
                            # 记录作业-知识点映射
                            assignment_knowledge_maps[assignment.id] = [kp['knowledge_point'].id for kp in assignment_knowledge]
                            
                except DoesNotExist:
                    continue
        
        # 创建数据集
        dataset = NeuralCDMDataset(
            student_ids, assignment_ids, knowledge_point_ids, scores, assignment_knowledge_maps
        )
        
        # 保存映射关系
        self.student_id_to_idx = dataset.student_id_to_idx
        self.knowledge_id_to_idx = dataset.knowledge_id_to_idx
        self.idx_to_student_id = {v: k for k, v in self.student_id_to_idx.items()}
        self.idx_to_knowledge_id = {v: k for k, v in self.knowledge_id_to_idx.items()}
        
        metadata = {
            'num_students': dataset.num_students,
            'num_assignments': dataset.num_assignments,
            'num_knowledge_points': dataset.num_knowledge_points,
            'num_samples': len(scores)
        }
        
        return dataset, metadata
    
    def train_model(self, course_id: int, epochs: int = 100, lr: float = 0.001, 
                   batch_size: int = 32, lambda_reg: float = 0.01) -> Dict:
        """
        训练NeuralCDM模型
        
        Args:
            course_id: 课程ID
            epochs: 训练轮数
            lr: 学习率
            batch_size: 批次大小
            lambda_reg: 正则化系数
            
        Returns:
            Dict: 训练结果
        """
        # 准备数据
        dataset, metadata = self.prepare_training_data(course_id)
        
        if metadata['num_samples'] < 10:
            return {
                'success': False,
                'message': '训练数据不足，至少需要10个样本'
            }
        
        # 创建数据加载器
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # 创建模型
        self.model = NeuralCDMModel(
            num_students=metadata['num_students'],
            num_knowledge_points=metadata['num_knowledge_points']
        ).to(self.device)
        
        # 定义优化器和损失函数
        optimizer = optim.Adam(self.model.parameters(), lr=lr, weight_decay=lambda_reg)
        criterion = nn.MSELoss()
        
        # 训练
        train_losses = []
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            for batch in dataloader:
                student_indices = batch['student_idx'].to(self.device)
                assignment_knowledge_points = batch['knowledge_points']
                scores = batch['score'].float().to(self.device)
                
                # 前向传播
                predicted_scores, _ = self.model(student_indices, assignment_knowledge_points)
                
                # 计算损失
                loss = criterion(predicted_scores, scores)
                
                # 反向传播
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                num_batches += 1
            
            avg_loss = epoch_loss / num_batches
            train_losses.append(avg_loss)
            
            if epoch % 20 == 0:
                print(f'Epoch {epoch}, Loss: {avg_loss:.4f}')
        
        # 保存模型
        model_path = f'neural_cdm_model_course_{course_id}.pth'
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'metadata': metadata,
            'mappings': {
                'student_id_to_idx': self.student_id_to_idx,
                'knowledge_id_to_idx': self.knowledge_id_to_idx
            }
        }, model_path)
        
        return {
            'success': True,
            'message': f'模型训练完成，最终损失: {train_losses[-1]:.4f}',
            'model_path': model_path,
            'metadata': metadata,
            'train_losses': train_losses
        }
    
    def predict_student_mastery(self, student_id: int, course_id: int) -> Dict:
        """
        预测学生知识点掌握度
        
        Args:
            student_id: 学生ID
            course_id: 课程ID
            
        Returns:
            Dict: 掌握度预测结果
        """
        if self.model is None:
            return {
                'success': False,
                'message': '模型未训练，请先训练模型'
            }
        
        if student_id not in self.student_id_to_idx:
            return {
                'success': False,
                'message': '学生不在训练数据中'
            }
        
        student_idx = self.student_id_to_idx[student_id]
        
        # 获取学生的知识点掌握度向量
        with torch.no_grad():
            student_embeddings = self.model.student_knowledge_embeddings[student_idx]  # [num_knowledge_points, knowledge_dim]
            
            # 计算每个知识点的掌握度（通过嵌入向量的范数或特定维度）
            mastery_scores = torch.norm(student_embeddings, dim=1)  # [num_knowledge_points]
            
            # 归一化到[0,1]区间
            mastery_scores = torch.sigmoid(mastery_scores)
        
        # 构建结果
        mastery_results = []
        for kp_idx, mastery in enumerate(mastery_scores):
            knowledge_id = self.idx_to_knowledge_id[kp_idx]
            mastery_results.append({
                'knowledge_point_id': knowledge_id,
                'mastery_level': mastery.item(),
                'mastery_percentage': round(mastery.item() * 100, 1)
            })
        
        # 按掌握度排序
        mastery_results.sort(key=lambda x: x['mastery_level'], reverse=True)
        
        return {
            'success': True,
            'student_id': student_id,
            'course_id': course_id,
            'mastery_results': mastery_results,
            'average_mastery': round(sum(r['mastery_level'] for r in mastery_results) / len(mastery_results), 3)
        }
    
    def update_database_mastery(self, course_id: int) -> Dict:
        """
        将模型预测的掌握度更新到数据库
        
        Args:
            course_id: 课程ID
            
        Returns:
            Dict: 更新结果
        """
        if self.model is None:
            return {
                'success': False,
                'message': '模型未训练，请先训练模型'
            }
        
        enrollments = StudentCourse.select().where(StudentCourse.course_id == course_id)
        updated_count = 0
        failed_count = 0
        
        for enrollment in enrollments:
            try:
                result = self.predict_student_mastery(enrollment.student_id, course_id)
                
                if result['success']:
                    # 更新数据库
                    for mastery_result in result['mastery_results']:
                        knowledge_point_id = mastery_result['knowledge_point_id']
                        mastery_level = mastery_result['mastery_level']
                        
                        record, created = StudentKnowledgePoint.get_or_create(
                            student_id=enrollment.student_id,
                            knowledge_point_id=knowledge_point_id,
                            defaults={'mastery_level': 0.0}
                        )
                        
                        record.mastery_level = mastery_level
                        record.last_interaction = datetime.now()
                        record.save()
                    
                    updated_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                print(f"更新学生 {enrollment.student_id} 掌握度失败: {e}")
        
        return {
            'success': True,
            'message': f'数据库更新完成: 成功 {updated_count} 个学生, 失败 {failed_count} 个学生',
            'updated_count': updated_count,
            'failed_count': failed_count
        }
    
    def analyze_knowledge_difficulty(self, course_id: int) -> Dict:
        """
        分析知识点难度
        
        Args:
            course_id: 课程ID
            
        Returns:
            Dict: 难度分析结果
        """
        if self.model is None:
            return {
                'success': False,
                'message': '模型未训练，请先训练模型'
            }
        
        # 获取所有学生的掌握度
        all_masteries = []
        for student_idx in range(self.model.num_students):
            student_id = self.idx_to_student_id[student_idx]
            result = self.predict_student_mastery(student_id, course_id)
            
            if result['success']:
                all_masteries.append(result['mastery_results'])
        
        if not all_masteries:
            return {
                'success': False,
                'message': '没有掌握度数据'
            }
        
        # 计算每个知识点的平均掌握度
        knowledge_stats = {}
        for kp_idx in range(self.model.num_knowledge_points):
            knowledge_id = self.idx_to_knowledge_id[kp_idx]
            
            masteries = []
            for student_masteries in all_masteries:
                for mastery in student_masteries:
                    if mastery['knowledge_point_id'] == knowledge_id:
                        masteries.append(mastery['mastery_level'])
                        break
            
            if masteries:
                avg_mastery = sum(masteries) / len(masteries)
                std_mastery = np.std(masteries)
                
                # 难度评估（掌握度越低越难）
                if avg_mastery >= 0.8:
                    difficulty = "简单"
                elif avg_mastery >= 0.6:
                    difficulty = "中等"
                elif avg_mastery >= 0.4:
                    difficulty = "困难"
                else:
                    difficulty = "很难"
                
                knowledge_stats[knowledge_id] = {
                    'average_mastery': round(avg_mastery, 3),
                    'std_mastery': round(std_mastery, 3),
                    'difficulty': difficulty,
                    'student_count': len(masteries)
                }
        
        return {
            'success': True,
            'knowledge_difficulty': knowledge_stats
        }
    
    @staticmethod
    def load_model(model_path: str, device: str = 'cpu') -> 'NeuralCDMService':
        """
        加载训练好的模型
        
        Args:
            model_path: 模型文件路径
            device: 设备
            
        Returns:
            NeuralCDMService: 加载了模型的服务实例
        """
        checkpoint = torch.load(model_path, map_location=device)
        
        service = NeuralCDMService(device)
        service.student_id_to_idx = checkpoint['mappings']['student_id_to_idx']
        service.knowledge_id_to_idx = checkpoint['mappings']['knowledge_id_to_idx']
        service.idx_to_student_id = {v: k for k, v in service.student_id_to_idx.items()}
        service.idx_to_knowledge_id = {v: k for k, v in service.knowledge_id_to_idx.items()}
        
        metadata = checkpoint['metadata']
        service.model = NeuralCDMModel(
            num_students=metadata['num_students'],
            num_knowledge_points=metadata['num_knowledge_points']
        ).to(device)
        service.model.load_state_dict(checkpoint['model_state_dict'])
        service.model.eval()
        
        return service 