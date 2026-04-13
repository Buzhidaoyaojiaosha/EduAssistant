# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI
import os

from app.utils.logging import logger


def chat_deepseek(messages):
    try:
        logger.debug("messages:\n", messages[0]['content'])
        logger.info("Generating response from DeepSeek")
        client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )

        if not response.choices[0].message.content:
            logger.error("Empty response from the model")
            return None

        logger.info("Successfully generated response")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return None