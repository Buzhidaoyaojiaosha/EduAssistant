import requests
import os
from app.utils.logging import logger


url = "https://api.siliconflow.cn/v1/chat/completions"


def chat_silicon(messages, model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"):  # 默认使用DeepSeek-R1-Distill-Qwen-32B模型
    headers = {
        "Authorization": "Bearer "+os.getenv("SILICON_API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": 4096,
        "stop": None,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.5,
        "n": 1,
        "response_format": {"type": "text"},
    }
    try:
        logger.debug("messages:\n", messages)
        logger.info(f"Generating response from {model}")
        response = requests.request("POST", url, json=payload, headers=headers)

        if not response.text:
            logger.error("Empty response from the model")
            return None

        logger.info("Successfully generated response")
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return None


if __name__ == '__main__':
    print(chat_silicon([
        {
            "role": "user",
            "content":"介绍一下Lambda-CDM模型"
        }
    ]))