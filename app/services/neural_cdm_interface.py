from app.services.neural_cdm_service import NeuralCDMService
from app.react.tools_register import register_as_tool
from typing import Dict, List
import os


class NeuralCDMInterface:
    """NeuralCDM 算法接口，提供简化的使用方式"""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.services = {}  # 缓存不同课程的服务实例
        
        # 确保模型目录存在
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
    
    @register_as_tool(roles=["teacher"])
    def train_course_model(self, course_id: int, epochs: int = 100, 
                          lr: float = 0.001, batch_size: int = 32) -> Dict:
        """
        训练指定课程的NeuralCDM模型
        
        Args:
            course_id: 课程ID
            epochs: 训练轮数
            lr: 学习率
            batch_size: 批次大小
            
        Returns:
            Dict: 训练结果
        """
        try:
            # 创建服务实例
            service = NeuralCDMService()
            
            # 训练模型
            result = service.train_model(
                course_id=course_id,
                epochs=epochs,
                lr=lr,
                batch_size=batch_size
            )
            
            if result['success']:
                # 缓存服务实例
                self.services[course_id] = service
                
                # 移动模型文件到指定目录
                model_path = result['model_path']
                new_path = os.path.join(self.model_dir, f"neural_cdm_course_{course_id}.pth")
                if os.path.exists(model_path):
                    os.rename(model_path, new_path)
                    result['model_path'] = new_path
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'训练失败: {str(e)}'
            }
    
    @register_as_tool(roles=["teacher", "student"])
    def predict_student_mastery(self, student_id: int, course_id: int) -> Dict:
        """
        预测学生知识点掌握度
        
        Args:
            student_id: 学生ID
            course_id: 课程ID
            
        Returns:
            Dict: 掌握度预测结果
        """
        try:
            # 获取或加载服务实例
            service = self._get_service(course_id)
            
            if service is None:
                return {
                    'success': False,
                    'message': f'课程 {course_id} 的模型未训练，请先训练模型'
                }
            
            return service.predict_student_mastery(student_id, course_id)
            
        except Exception as e:
            return {
                'success': False,
                'message': f'预测失败: {str(e)}'
            }
    
    @register_as_tool(roles=["teacher"])
    def update_course_mastery(self, course_id: int) -> Dict:
        """
        更新课程所有学生的知识点掌握度到数据库
        
        Args:
            course_id: 课程ID
            
        Returns:
            Dict: 更新结果
        """
        try:
            # 获取或加载服务实例
            service = self._get_service(course_id)
            
            if service is None:
                return {
                    'success': False,
                    'message': f'课程 {course_id} 的模型未训练，请先训练模型'
                }
            
            return service.update_database_mastery(course_id)
            
        except Exception as e:
            return {
                'success': False,
                'message': f'更新失败: {str(e)}'
            }
    
    @register_as_tool(roles=["teacher"])
    def analyze_course_difficulty(self, course_id: int) -> Dict:
        """
        分析课程知识点难度
        
        Args:
            course_id: 课程ID
            
        Returns:
            Dict: 难度分析结果
        """
        try:
            # 获取或加载服务实例
            service = self._get_service(course_id)
            
            if service is None:
                return {
                    'success': False,
                    'message': f'课程 {course_id} 的模型未训练，请先训练模型'
                }
            
            return service.analyze_knowledge_difficulty(course_id)
            
        except Exception as e:
            return {
                'success': False,
                'message': f'分析失败: {str(e)}'
            }
    
    @register_as_tool(roles=["teacher"])
    def get_course_mastery_summary(self, course_id: int) -> Dict:
        """
        获取课程掌握度摘要
        
        Args:
            course_id: 课程ID
            
        Returns:
            Dict: 课程掌握度摘要
        """
        try:
            # 获取或加载服务实例
            service = self._get_service(course_id)
            
            if service is None:
                return {
                    'success': False,
                    'message': f'课程 {course_id} 的模型未训练，请先训练模型'
                }
            
            # 获取所有学生的掌握度
            from app.models.course import StudentCourse
            enrollments = StudentCourse.select().where(StudentCourse.course_id == course_id)
            
            all_masteries = []
            for enrollment in enrollments:
                result = service.predict_student_mastery(enrollment.student_id, course_id)
                if result['success']:
                    all_masteries.append({
                        'student_id': enrollment.student_id,
                        'student_name': enrollment.student.name,
                        'mastery_results': result['mastery_results'],
                        'average_mastery': result['average_mastery']
                    })
            
            if not all_masteries:
                return {
                    'success': False,
                    'message': '没有掌握度数据'
                }
            
            # 计算课程整体统计
            course_average = sum(m['average_mastery'] for m in all_masteries) / len(all_masteries)
            
            # 按平均掌握度排序
            all_masteries.sort(key=lambda x: x['average_mastery'], reverse=True)
            
            return {
                'success': True,
                'course_id': course_id,
                'total_students': len(all_masteries),
                'course_average_mastery': round(course_average, 3),
                'student_masteries': all_masteries,
                'top_students': all_masteries[:5],  # 前5名学生
                'bottom_students': all_masteries[-5:]  # 后5名学生
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取摘要失败: {str(e)}'
            }
    
    def _get_service(self, course_id: int) -> NeuralCDMService:
        """
        获取或加载服务实例
        
        Args:
            course_id: 课程ID
            
        Returns:
            NeuralCDMService: 服务实例
        """
        # 检查缓存
        if course_id in self.services:
            return self.services[course_id]
        
        # 尝试加载已训练的模型
        model_path = os.path.join(self.model_dir, f"neural_cdm_course_{course_id}.pth")
        
        if os.path.exists(model_path):
            try:
                service = NeuralCDMService.load_model(model_path)
                self.services[course_id] = service
                return service
            except Exception as e:
                print(f"加载模型失败: {e}")
                return None
        
        return None
    
    def list_trained_models(self) -> List[Dict]:
        """
        列出所有已训练的模型
        
        Returns:
            List[Dict]: 模型列表
        """
        models = []
        
        for filename in os.listdir(self.model_dir):
            if filename.startswith("neural_cdm_course_") and filename.endswith(".pth"):
                try:
                    course_id = int(filename.split("_")[-1].split(".")[0])
                    model_path = os.path.join(self.model_dir, filename)
                    
                    # 获取文件信息
                    import time
                    stat = os.stat(model_path)
                    created_time = time.ctime(stat.st_mtime)
                    
                    models.append({
                        'course_id': course_id,
                        'model_path': model_path,
                        'file_size': stat.st_size,
                        'created_time': created_time
                    })
                except:
                    continue
        
        return models


# 全局接口实例
neural_cdm_interface = NeuralCDMInterface()


# 便捷函数
def train_neural_cdm_model(course_id: int, **kwargs) -> Dict:
    """训练NeuralCDM模型"""
    return neural_cdm_interface.train_course_model(course_id, **kwargs)


def predict_student_mastery_neural_cdm(student_id: int, course_id: int) -> Dict:
    """使用NeuralCDM预测学生掌握度"""
    return neural_cdm_interface.predict_student_mastery(student_id, course_id)


def update_course_mastery_neural_cdm(course_id: int) -> Dict:
    """使用NeuralCDM更新课程掌握度"""
    return neural_cdm_interface.update_course_mastery(course_id)


def analyze_course_difficulty_neural_cdm(course_id: int) -> Dict:
    """使用NeuralCDM分析课程难度"""
    return neural_cdm_interface.analyze_course_difficulty(course_id) 