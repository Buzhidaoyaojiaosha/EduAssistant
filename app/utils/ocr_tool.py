from typing import Dict, List, Tuple, Optional, Any, Union, cast, Sequence
import os
import re
import sys
import os

# 临时修改 sys.path，确保标准库的 logging 模块优先被导入
original_path = sys.path.copy()
sys.path = [p for p in sys.path if 'EduAssistant' not in p]  # 移除项目路径
import logging  # 现在会导入标准库的 logging
sys.path = original_path  # 恢复原始路径

import numpy as np
from PIL import Image, ImageDraw
# 使用 PaddleOCR 替代 EasyOCR
from paddleocr import PaddleOCR

class OCRTool:
    def __init__(self):
        """
        初始化OCR工具类
        """
        # 禁用PaddleOCR的日志输出
        import logging
        logging.getLogger("ppocr").setLevel(logging.ERROR)
        import warnings
        warnings.filterwarnings("ignore")

        # 初始化 PaddleOCR，禁用详细日志
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        self.np = np
        self.Image = Image
        self.ImageDraw = ImageDraw
        self.re = re
        self.os = os

    def process_image(self, image_path: str, target_question: Optional[str] = None, debug: bool = False, answer_image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        处理图片，提取文本或特定题目答案
        
        Args:
            image_path: 图像文件路径
            target_question: 目标题号，如"17"，不指定则返回所有文本
            debug: 是否启用调试模式，生成标记答案区域的图像
            answer_image_path: 答案区域图片保存路径
            
        Returns:
            包含OCR结果和特定答案的字典
        """
        if not image_path or not os.path.exists(image_path):
            raise ValueError(f"图像文件不存在: {image_path}")

        # 使用 PaddleOCR 识别文本
        result = self.ocr.ocr(image_path, cls=True)

        # 转换结果格式以兼容现有代码
        ocr_result_with_position = []
        for line in result:
            for item in line:
                bbox = item[0]  # 边界框坐标
                text = item[1][0]  # 识别的文本
                confidence = item[1][1]  # 置信度
                # 转换为与 EasyOCR 兼容的格式
                formatted_bbox = [
                    [bbox[0][0], bbox[0][1]],  # 左上
                    [bbox[1][0], bbox[1][1]],  # 右上
                    [bbox[2][0], bbox[2][1]],  # 右下
                    [bbox[3][0], bbox[3][1]]   # 左下
                ]
                ocr_result_with_position.append((formatted_bbox, text, confidence))

        # 提取纯文本结果 - 修复类型错误
        ocr_result = []
        for item in ocr_result_with_position:
            if isinstance(item, (list, tuple)) and len(item) > 1:
                ocr_result.append(item[1])

        # 如果指定了目标题号，则尝试提取该题的答案
        extracted_answer = None
        answer_region = None
        saved_answer_image_path = None  # 修改变量名，避免覆盖参数

        if target_question:
            # 转换为正确的类型
            typed_result = cast(List[Tuple[List, str, float]], ocr_result_with_position)
            extracted_answer, answer_region = self._extract_specific_question_answer(
                typed_result, target_question, image_path, debug
            )

            # 如果找到了答案区域，截取答案图片
            if answer_region:
                saved_answer_image_path = self._crop_answer_region(image_path, answer_region, target_question, answer_image_path)
                print(f"答案图片保存路径: {saved_answer_image_path}")  # 添加调试信息

        result = {
            "ocr_result": ocr_result,
            "specific_answer": extracted_answer,
            "answer_region": answer_region,  # 返回答案区域坐标，方便前端展示
            "answer_image_path": saved_answer_image_path  # 使用新变量名
        }

        return result

    def _crop_answer_region(self, image_path: str, region: List, question_num: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        截取答案区域并保存为新图片
    
        Args:
            image_path: 原始图像文件路径
            region: 答案区域坐标
            question_num: 题号
            output_path: 输出图片路径，如果提供则使用此路径保存图片
    
        Returns:
            截取的答案图片路径，如果截取失败则返回None
        """
        if not region:
            return None
    
        try:
            # 读取原始图像
            image = Image.open(image_path)
    
            # 计算边界框的左上角和右下角坐标
            min_x = min(point[0] for point in region)
            min_y = min(point[1] for point in region)
            max_x = max(point[0] for point in region)
            max_y = max(point[1] for point in region)
    
            # 添加一些边距，使截图更美观
            padding = 10
            min_x = max(0, min_x - padding)
            min_y = max(0, min_y - padding)
            max_x = min(image.width, max_x + padding)
            max_y = min(image.height, max_y + padding)
    
            # 截取答案区域
            cropped_image = image.crop((min_x, min_y, max_x, max_y))
    
            # 保存截取的图片
            if output_path:
                # 如果提供了输出路径，直接使用
                save_path = output_path
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                print(f"使用指定路径保存答案图片: {save_path}")  # 添加调试信息
            else:
                # 否则使用默认路径
                output_dir = os.path.dirname(image_path)
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                save_path = os.path.join(output_dir, f"{name}_answer_q{question_num}{ext}")
                print(f"使用默认路径保存答案图片: {save_path}")  # 添加调试信息
    
            cropped_image.save(save_path)
            print(f"已保存答案区域截图: {save_path}")
    
            return save_path
    
        except Exception as e:
            print(f"截取答案区域时出错: {e}")
            return None

    def _extract_specific_question_answer(self,
                                          ocr_result_with_position: List[Tuple[List, str, float]],
                                          target_question: str,
                                          image_path: str,
                                          debug: bool = False) -> Tuple[str, Optional[List]]:
        """
        从OCR结果中提取特定题号的答案

        Args:
            ocr_result_with_position: 包含位置信息的OCR结果
            target_question: 目标题号，如"17"
            image_path: 图像文件路径，用于可视化和调试
            debug: 是否启用调试模式

        Returns:
            提取的答案文本和答案区域坐标的元组
        """
        # 题号可能的模式：第17题、17、17.、17、、17：等
        question_patterns = [
            f"第{target_question}题",
            f"第{target_question}道题",
            f"{target_question}题",
            f"{target_question}道题",
            f"{target_question}[.、:：]",
            f"{target_question}\\.",
            f"{target_question}、",
            f"{target_question}:",
            f"{target_question}：",
            f"^{target_question}$"  # 单独的数字
        ]

        # 查找目标题号的位置
        target_idx = -1
        target_bbox = None

        for idx, (bbox, text, _) in enumerate(ocr_result_with_position):
            # 检查文本是否匹配任一题号模式
            for pattern in question_patterns:
                if re.search(pattern, text):
                    target_idx = idx
                    target_bbox = bbox
                    break
            if target_idx != -1:
                break

        if target_idx == -1:
            return "未找到指定题号", None

        # 获取目标题号的位置信息
        target_text = ocr_result_with_position[target_idx][1]

        # 查找下一题的位置
        next_question = str(int(target_question) + 1)
        next_patterns = [
            f"第{next_question}题",
            f"第{next_question}道题",
            f"{next_question}题",
            f"{next_question}道题",
            f"{next_question}[.、:：]",
            f"{next_question}\\.",
            f"{next_question}、",
            f"{next_question}:",
            f"{next_question}：",
            f"^{next_question}$"  # 单独的数字
        ]

        next_idx = -1
        next_bbox = None

        for idx, (bbox, text, _) in enumerate(ocr_result_with_position):
            if idx <= target_idx:
                continue

            for pattern in next_patterns:
                if re.search(pattern, text):
                    next_idx = idx
                    next_bbox = bbox
                    break
            if next_idx != -1:
                break

        # 提取答案的策略
        answer_texts = []
        answer_region = None

        # 确保target_bbox不为None
        if target_bbox is None:
            return "找到题号但无法确定位置", None

        # 计算目标题号的中心位置
        target_center_x = sum([p[0] for p in target_bbox]) / 4
        target_center_y = sum([p[1] for p in target_bbox]) / 4

        # 如果找到了下一题，则提取两题之间的所有文本
        if next_idx != -1 and next_bbox is not None:
            # 计算下一题的中心位置
            next_center_x = sum([p[0] for p in next_bbox]) / 4
            next_center_y = sum([p[1] for p in next_bbox]) / 4

            # 确定答案区域
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')

            # 收集当前题和下一题之间的所有文本
            for idx, (bbox, text, _) in enumerate(ocr_result_with_position):
                if idx == target_idx:
                    # 排除题号本身，只保留题号后面的部分
                    for pattern in question_patterns:
                        match = re.search(pattern, target_text)
                        if match:
                            # 提取题号后面的部分作为答案的一部分
                            answer_part = target_text[match.end():].strip()
                            if answer_part:
                                answer_texts.append(answer_part)
                    continue

                if idx == next_idx:
                    continue

                # 计算当前文本的中心位置
                current_center_x = sum([p[0] for p in bbox]) / 4
                current_center_y = sum([p[1] for p in bbox]) / 4

                # 判断是否在当前题和下一题之间
                is_between_questions = False

                # 垂直布局：当前文本在当前题下方且在下一题上方
                if target_center_y < current_center_y < next_center_y:
                    is_between_questions = True

                # 水平布局：当前文本在当前题右侧且在下一题左侧
                elif target_center_x < current_center_x < next_center_x:
                    is_between_questions = True

                if is_between_questions:
                    answer_texts.append(text)

                    # 更新答案区域边界
                    for point in bbox:
                        min_x = min(min_x, point[0])
                        min_y = min(min_y, point[1])
                        max_x = max(max_x, point[0])
                        max_y = max(max_y, point[1])

            # 设置答案区域
            if min_x != float('inf'):
                answer_region = [[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y]]

        # 如果没有找到下一题或没有提取到答案，尝试其他策略
        if not answer_texts:
            # 查找可能的答案文本（在题号下方或右侧的几个文本块）
            candidate_answers = []

            for idx, (bbox, text, _) in enumerate(ocr_result_with_position):
                if idx == target_idx:
                    continue

                # 计算当前文本的中心位置
                current_center_x = sum([p[0] for p in bbox]) / 4
                current_center_y = sum([p[1] for p in bbox]) / 4

                # 计算与题号的距离
                distance_x = current_center_x - target_center_x
                distance_y = current_center_y - target_center_y

                # 判断是否是同一行（右侧）或下一行
                is_same_line = abs(distance_y) < 20 and distance_x > 0
                is_next_line = distance_y > 0 and distance_y < 100

                if is_same_line or is_next_line:
                    # 计算优先级：同行优先，然后是距离近的
                    priority = 1 if is_same_line else 2
                    distance = (distance_x ** 2 + distance_y ** 2) ** 0.5
                    candidate_answers.append((text, priority, distance, bbox))

            # 根据优先级和距离排序候选答案
            if candidate_answers:
                # 先按优先级（同行优先），再按距离排序
                candidate_answers.sort(key=lambda x: (x[1], x[2]))

                # 提取前几个最可能的答案
                for text, _, _, bbox in candidate_answers[:3]:  # 取前3个最可能的答案
                    answer_texts.append(text)

                    # 更新答案区域
                    if answer_region is None:
                        answer_region = bbox
                    else:
                        # 扩展答案区域
                        for i in range(4):
                            answer_region[i][0] = min(answer_region[i][0], bbox[i][0])
                            answer_region[i][1] = min(answer_region[i][1], bbox[i][1])

        # 如果仍然没有提取到答案，尝试直接提取题号后面的部分
        if not answer_texts:
            for pattern in question_patterns:
                match = re.search(pattern, target_text)
                if match:
                    # 提取题号后面的部分作为答案
                    answer_part = target_text[match.end():].strip()
                    if answer_part:
                        answer_texts.append(answer_part)
                        answer_region = target_bbox
                        break

        # 如果还是没有提取到答案，返回提示信息
        if not answer_texts:
            return "找到题号但未能提取到答案", target_bbox

        # 可视化答案区域（用于调试）
        if debug and answer_region is not None:
            try:
                self._visualize_answer_region(image_path, answer_region, target_question)
            except Exception as e:
                print(f"可视化答案区域时出错: {e}")

        return " ".join(answer_texts), answer_region

    def _visualize_answer_region(self, image_path: str, region: List, question_num: str) -> None:
        """
        可视化标记答案区域（用于调试）

        Args:
            image_path: 图像文件路径
            region: 答案区域坐标
            question_num: 题号
        """
        if not region:
            return

        try:
            # 读取原始图像
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)

            # 绘制答案区域边框
            draw.polygon(region, outline=(255, 0, 0), width=3)

            # 添加题号标记
            draw.text((region[0][0], region[0][1] - 20), f"第{question_num}题答案区域", fill=(255, 0, 0))

            # 保存标记后的图像
            output_dir = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_marked_q{question_num}{ext}")

            image.save(output_path)
            print(f"已保存标记答案区域的图像: {output_path}")

        except Exception as e:
            print(f"可视化答案区域时出错: {e}")

if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) >= 3:
        # 从命令行参数获取图像路径和题号
        image_path = sys.argv[1]
        target_question = sys.argv[2]
        debug = False
        output_file = None
        answer_image_path = None

        # 如果有第三个参数，作为输出文件路径
        if len(sys.argv) >= 4:
            output_file = sys.argv[3]

        # 如果有第四个参数，作为答案图片保存路径
        if len(sys.argv) >= 5:
            answer_image_path = sys.argv[4]
            print(f"接收到的答案图片保存路径: {answer_image_path}")  # 添加调试信息

        # 如果有第五个参数且为"debug"，则启用调试模式
        if len(sys.argv) >= 6 and sys.argv[5].lower() == "debug":
            debug = True

        # 创建OCR工具实例
        ocr_tool = OCRTool()

        try:
            # 禁用PaddleOCR的日志输出
            import logging
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            import warnings
            warnings.filterwarnings("ignore")

            # 处理图像并提取特定题目的答案
            result = ocr_tool.process_image(image_path, target_question=target_question, debug=debug, answer_image_path=answer_image_path)
            answer = result["specific_answer"]

            # 简化输出，只输出答案
            answer_text = f"第{target_question}题的答案: {answer}"
            print(answer_text)

            # 如果有截取的答案图片，输出路径
            if result.get("answer_image_path"):
                print(f"答案区域截图已保存: {result['answer_image_path']}")
            else:
                print(f"警告: 未能生成答案区域截图")

            # 如果指定了输出文件，将结果写入文件
            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"图片路径: {image_path}\n")
                        f.write(f"题号: {target_question}\n")
                        f.write(f"答案: {answer}\n")

                        # 添加答案截图路径
                        if result.get("answer_image_path"):
                            f.write(f"答案区域截图: {result['answer_image_path']}\n")

                        f.write("\n")

                        # 添加详细OCR结果，但格式更清晰
                        f.write("详细OCR结果:\n")
                        for text in result["ocr_result"]:
                            f.write(f"- {text}\n")

                        # 添加答案区域信息
                        if result["answer_region"]:
                            f.write("\n答案区域坐标:\n")
                            f.write(str(result["answer_region"]))
                except Exception as e:
                    print(f"写入输出文件时出错: {e}")
        except Exception as e:
            error_msg = f"OCR处理失败: {e}"
            print(error_msg)

            # 如果指定了输出文件，将错误信息写入文件
            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"OCR处理失败: {e}\n")
                except:
                    pass
    else:
        print("用法: python ocr_tool.py <图片路径> <题号> [输出文件路径] [debug]")
        print("示例: python ocr_tool.py image.png 17 output.txt debug")
        # 如果没有足够的命令行参数，则运行示例代码
        # 创建OCR工具实例
        ocr_tool = OCRTool()

        # 示例1：提取所有文本
        result = ocr_tool.process_image("E:\\Grade_6\\student_helper\\ceshiOCR\\tuxiangfenge\\171819.png")
        all_text = result["ocr_result"]
        print(f"识别到的所有文本: {all_text}")

        # 示例2：提取特定题目的答案
        target_question = "19"  # 可以根据需要修改题号
        result = ocr_tool.process_image(
            "E:\\Grade_6\\student_helper\\ceshiOCR\\tuxiangfenge\\171819.png",
            target_question=target_question,
            debug=True  # 启用调试模式，生成标记答案区域的图像
        )
        answer = result["specific_answer"]
        print(f"第{target_question}题的答案: {answer}")

        # 获取答案区域坐标（可用于前端高亮显示）
        answer_region = result["answer_region"]

        # 获取答案区域截图路径
        answer_image_path = result.get("answer_image_path")
        if answer_image_path:
            print(f"答案区域截图已保存: {answer_image_path}")
    