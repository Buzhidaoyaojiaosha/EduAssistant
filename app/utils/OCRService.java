package org.studenthelper.helper_server_v1.Utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.*;

@Service
public class OCRService {

    private static final String PYTHON_PATH = "D:\\anaconda3\\envs\\learnerHelper\\python";
    private static final String OCR_SCRIPT_PATH = "e:\\Grade_6\\student_helper\\helper_server_V1\\src\\main\\java\\org\\studenthelper\\helper_server_v1\\Utils\\ocr_tool.py";
    private static final String TEMP_DIR = "e:\\Grade_6\\student_helper\\helper_server_V1\\temp";

    /**
     * 从图片中提取答案
     *
     * @param file           上传的图片文件
     * @param questionNumber 题目编号
     * @return 提取的答案
     */
    public String extractAnswerFromImage(MultipartFile file, String questionNumber) throws IOException {
        // 确保临时目录存在
        File tempDirFile = new File(TEMP_DIR);
        if (!tempDirFile.exists()) {
            tempDirFile.mkdirs();
        }

        // 保存上传的文件到临时目录
        String originalFilename = file.getOriginalFilename();
        String fileExtension = originalFilename.substring(originalFilename.lastIndexOf("."));
        String tempFileName = UUID.randomUUID().toString() + fileExtension;
        Path tempFilePath = Paths.get(TEMP_DIR, tempFileName);

        Files.copy(file.getInputStream(), tempFilePath, StandardCopyOption.REPLACE_EXISTING);
        System.out.println("用户上传图片已保存至临时文件: " + tempFilePath);

        // 创建OCR结果输出目录
        File ocrOutputDir = new File("E:\\Grade_6\\student_helper\\helper_server_V1\\ocr_results");
        if (!ocrOutputDir.exists()) {
            ocrOutputDir.mkdirs();
        }

        // 创建OCR结果文件
        String timestamp = String.valueOf(System.currentTimeMillis());
        File ocrOutputFile = new File(ocrOutputDir, "ocr_result_" + questionNumber + "_" + timestamp + ".txt");

        // 调用Python脚本进行OCR
        try {
            // 构建命令
            List<String> command = new ArrayList<>();
            command.add(PYTHON_PATH);
            command.add(OCR_SCRIPT_PATH);
            command.add(tempFilePath.toString());
            command.add(questionNumber);
            command.add(ocrOutputFile.getAbsolutePath());

            System.out.println("执行命令: " + String.join(" ", command));

            // 执行命令
            ProcessBuilder processBuilder = new ProcessBuilder(command);
            processBuilder.redirectErrorStream(true);
            Process process = processBuilder.start();

            // 读取输出
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
            StringBuilder output = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
                System.out.println("OCR输出: " + line);
            }

            // 等待进程完成
            int exitCode = process.waitFor();
            System.out.println("OCR进程退出码: " + exitCode);

            if (exitCode != 0) {
                System.err.println("OCR脚本执行失败，错误码: " + exitCode);
                return "OCR处理失败，错误码: " + exitCode;
            }

            // 从输出文件中读取答案
            if (ocrOutputFile.exists()) {
                try {
                    List<String> lines = Files.readAllLines(ocrOutputFile.toPath(), StandardCharsets.UTF_8);
                    for (String fileLine : lines) {
                        if (fileLine.startsWith("答案:")) {
                            String answer = fileLine.substring(3).trim();
                            System.out.println("题目ID: " + questionNumber + " - 从文件中提取的OCR答案: " + answer);
                            return answer;
                        }
                    }
                } catch (Exception e) {
                    System.err.println("读取OCR结果文件失败: " + e.getMessage());
                    e.printStackTrace();
                }
            } else {
                System.err.println("OCR结果文件不存在: " + ocrOutputFile.getAbsolutePath());
            }

            // 如果无法从文件中读取答案，返回提示信息
            System.out.println("题目ID: " + questionNumber + " - 无法从OCR结果中提取答案");
            return "无法从OCR结果中提取答案，请检查图片质量或OCR配置";
        } catch (Exception e) {
            e.printStackTrace();
            throw new IOException("OCR处理失败: " + e.getMessage());
        } finally {
            // 清理临时文件
            try {
                Files.deleteIfExists(tempFilePath);
            } catch (IOException e) {
                System.err.println("删除临时文件失败: " + e.getMessage());
                // 忽略删除临时文件的错误
            }
        }
    }

    /**
     * 修改Python脚本以支持命令行参数
     */
    public void ensureScriptSupportsCommandLine() throws IOException {
        // 检查OCR脚本是否存在
        File scriptFile = new File(OCR_SCRIPT_PATH);
        if (!scriptFile.exists()) {
            throw new IOException("OCR脚本文件不存在: " + OCR_SCRIPT_PATH);
        }

        // 这里可以添加代码来检查脚本是否支持命令行参数
        // 如果不支持，可以修改脚本文件
    }

    /**
     * 从图片中提取答案文本和答案区域图片
     *
     * @param file           上传的图片文件
     * @param questionNumber 题号
     * @return 包含答案文本和答案区域图片路径的Map
     */
    public Map<String, Object> extractAnswerAndImageFromImage(MultipartFile file, String questionNumber) throws IOException, InterruptedException {
        // 确保临时目录存在
        File tempDirFile = new File(TEMP_DIR);
        if (!tempDirFile.exists()) {
            tempDirFile.mkdirs();
        }

        // 保存上传的文件到临时目录
        String originalFilename = file.getOriginalFilename();
        String fileExtension = originalFilename.substring(originalFilename.lastIndexOf("."));
        String tempFileName = UUID.randomUUID().toString() + fileExtension;
        Path tempFilePath = Paths.get(TEMP_DIR, tempFileName);

        Files.copy(file.getInputStream(), tempFilePath, StandardCopyOption.REPLACE_EXISTING);
        System.out.println("用户上传图片已保存至临时文件: " + tempFilePath);

        // 创建OCR结果输出目录
        File ocrOutputDir = new File("E:\\Grade_6\\student_helper\\helper_server_V1\\ocr_results");
        if (!ocrOutputDir.exists()) {
            ocrOutputDir.mkdirs();
        }

        // 创建OCR结果文件和答案图片目录
        String timestamp = String.valueOf(System.currentTimeMillis());
        File ocrOutputFile = new File(ocrOutputDir, "ocr_result_" + questionNumber + "_" + timestamp + ".txt");
        File answerImagesDir = new File(ocrOutputDir, "answer_images");
        if (!answerImagesDir.exists()) {
            answerImagesDir.mkdirs();
        }

        // 答案图片路径
        String answerImageFileName = "answer_" + questionNumber + "_" + timestamp + fileExtension;
        String answerImagePath = answerImagesDir.getAbsolutePath() + File.separator + answerImageFileName;

        Map<String, Object> result = new HashMap<>();

        try {
            // 构建命令 - 添加参数用于保存答案区域图片
            List<String> command = new ArrayList<>();
            command.add(PYTHON_PATH);
            command.add(OCR_SCRIPT_PATH);
            command.add(tempFilePath.toString());
            command.add(questionNumber);
            command.add(ocrOutputFile.getAbsolutePath());
            command.add(answerImagePath); // 添加答案图片保存路径参数

            System.out.println("执行命令: " + String.join(" ", command));

            // 执行命令
            ProcessBuilder processBuilder = new ProcessBuilder(command);
            processBuilder.redirectErrorStream(true);
            Process process = processBuilder.start();

            // 读取输出
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
            StringBuilder output = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
                System.out.println("OCR输出: " + line);
            }

            // 等待进程完成
            int exitCode = process.waitFor();
            System.out.println("OCR进程退出码: " + exitCode);

            if (exitCode != 0) {
                System.err.println("OCR脚本执行失败，错误码: " + exitCode);
                result.put("answer", "OCR处理失败，错误码: " + exitCode);
                return result;
            }

            // 从输出文件中读取答案
            String answer = "无法从OCR结果中提取答案";
            if (ocrOutputFile.exists()) {
                try {
                    List<String> lines = Files.readAllLines(ocrOutputFile.toPath(), StandardCharsets.UTF_8);
                    for (String fileLine : lines) {
                        if (fileLine.startsWith("答案:")) {
                            answer = fileLine.substring(3).trim();
                            System.out.println("题目ID: " + questionNumber + " - 从文件中提取的OCR答案: " + answer);
                            break;
                        }
                    }
                } catch (Exception e) {
                    System.err.println("读取OCR结果文件失败: " + e.getMessage());
                    e.printStackTrace();
                }
            } else {
                System.err.println("OCR结果文件不存在: " + ocrOutputFile.getAbsolutePath());
            }

            // 检查答案图片是否生成
            File answerImageFile = new File(answerImagePath);
            if (answerImageFile.exists()) {
                System.out.println("答案区域图片已保存: " + answerImagePath);
                result.put("answer_image_path", answerImagePath);
            } else {
                System.err.println("答案区域图片未生成: " + answerImagePath);
                result.put("answer_image_path", null);
            }

            result.put("answer", answer);

        } catch (Exception e) {
            System.err.println("OCR处理失败: " + e.getMessage());
            e.printStackTrace();
            result.put("answer", "OCR处理异常: " + e.getMessage());
            result.put("answer_image_path", null);
        } finally {
            // 清理临时文件
            try {
                Files.deleteIfExists(tempFilePath);
            } catch (IOException e) {
                System.err.println("删除临时文件失败: " + e.getMessage());
            }
        }

        return result;
    }
}