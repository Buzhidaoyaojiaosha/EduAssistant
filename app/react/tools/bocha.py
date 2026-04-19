import requests
import json
from app.react.tools_register import register_as_tool
from app.config import Config

url = Config.BOCHA_API_URL
api_key = Config.BOCHA_API_KEY or ""


@register_as_tool(roles=["student", "teacher"])
def bocha_search(query: str) -> str:

    summary = True
    count = Config.BOCHA_SEARCH_COUNT
    page = 1

    payload = json.dumps({
        "query": query,
        "summary": summary,
        "count": count,
        "page": page
    })

    headers = {
        'Authorization': 'Bearer ' + api_key,
        'Content-Type': 'application/json'
    }

    if not api_key:
        return "Bocha API key is not configured"

    try:
        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=payload,
            timeout=Config.BOCHA_SEARCH_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get('data', {}).get('webPages', {}).get('value', []))
    except Exception as e:
        return f"Bocha search failed: {str(e)}"

if __name__ == "__main__":
    query = "Lambda-CDM"
    response = bocha_search(query)
    #print(response)
    #print(response['data']['webPages']['value'][0]['summary'])
    #print(response['data']['webPages']['value'][0]['url'])
    print(f"{response}")