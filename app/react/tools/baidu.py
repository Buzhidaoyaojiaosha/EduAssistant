import requests
import json
from app.react.tools_register import register_as_tool
from app.config import Config


@register_as_tool(roles=["student", "teacher"])
def baidu_search(query: str) -> str:
    """使用API方式执行百度搜索并返回前几条结果摘要。"""
    if not query or not str(query).strip():
        return "Baidu search query is empty"

    if not Config.BAIDU_SEARCH_API_KEY:
        return "Baidu search API key is not configured"

    try:
        headers = {
            "X-Appbuilder-Authorization": f"Bearer {Config.BAIDU_SEARCH_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": str(query),
                }
            ],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [
                {
                    "type": "web",
                    "top_k": max(1, min(50, Config.BAIDU_SEARCH_TOP_K)),
                }
            ],
        }

        resp = requests.post(
            Config.BAIDU_SEARCH_API_URL,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False),
            timeout=Config.BAIDU_SEARCH_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()

        references = payload.get("references", [])

        results = []
        for item in references:
            title = str(item.get("title", "")).strip()
            link = str(item.get("url", "")).strip()
            if not title:
                continue
            results.append({
                "title": title,
                "link": link,
                "snippet": item.get("content", ""),
                "date": item.get("date", ""),
                "type": item.get("type", ""),
            })

        if not results:
            if payload.get("code") or payload.get("message"):
                return f"Baidu search failed: code={payload.get('code')} message={payload.get('message')}"
            return "No Baidu results found"

        return json.dumps({"query": query, "top_results": results}, ensure_ascii=False)
    except Exception as e:
        return f"Baidu search failed: {str(e)}"
