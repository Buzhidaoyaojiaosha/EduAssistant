import os
from googleapiclient.discovery import build
import httplib2
from app.react.tools_register import register_as_tool
# import requests
# from bs4 import BeautifulSoup
from app.config import Config as Config
"""
** 关于搜索API **
请自行配置环境变量，增加以下内容：

GOOGLE_SEARCH_CX: (fill in your cx id value)
GOOGLE_SEARCH_API_KEY: (fill in your api key value)

** 关于Google联网问题 ** 
如因防火墙问题无法联网，需要配置代理。环境变量：GOOGLE_SEARCH_PROXY。
"""
api_key = Config.GOOGLE_SEARCH_API_KEY
cx = Config.GOOGLE_SEARCH_CX
proxy = Config.GOOGLE_SEARCH_PROXY

if proxy is not "NO_PROXY":
    # 设置代理和超时时间
    http = httplib2.Http(proxy_info=httplib2.ProxyInfo(httplib2.socks.PROXY_TYPE_HTTP, "127.0.0.1", 7890), timeout=60)
else:
    # 不设置代理
    http = httplib2.Http()

def google_search(query):
    """
    直接使用api搜索获得结果
    :param query: 搜索关键字
    """
    with build('customsearch', 'v1', developerKey=api_key) as service:
        print(f'=====================================================\nSearch on Google\nquery: {query}, \napi: {api_key}, \ncx: {cx}')
        res = (
            service.cse()
            .list(
                q=query,
                cx=cx
            )
            .execute(http=http)
        )
    # return res.get('items', [])
    return res

# def fetch_page_content(url):
#     try:
#         response = requests.get(url)
#         if response.status_code == 200:
#             soup = BeautifulSoup(response.text, 'html.parser')
#             paragraphs = soup.find_all('p')
#             content = ' '.join([para.get_text() for para in paragraphs])
#             return content
#         else:
#             return None
#     except Exception as e:
#         print(f'Error fetching {url}: {e}')
#         return None

# def web_search(query : str) -> str:
#     return fetch_page_content(google_search(query)[0]['link'])


if __name__ == '__main__':
    print(google_search('软件测试理论'))
    # print(fetch_page_content('Group theory'))
