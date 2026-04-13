import requests
import json

url = "https://api.bochaai.com/v1/web-search"
api_key = ""


def bocha_search(query: str) -> str:

    summary=True
    count=3
    page=1

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

    response = requests.request("POST", url, headers=headers, data=payload)
    return str(response.json()['data']['webPages']['value'])

if __name__ == "__main__":
    query = "Lambda-CDM"
    response = bocha_search(query)
    #print(response)
    #print(response['data']['webPages']['value'][0]['summary'])
    #print(response['data']['webPages']['value'][0]['url'])
    print(f"{response}")