from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup
import yaml

google_config_path = '.\\credentials\\google.yml'
with open(google_config_path, 'r') as f:
    google_config = yaml.safe_load(f)
    api_key = google_config['api_key']
    cx      = google_config['cx']

def google_search(query):
    with build('customsearch', 'v1', developerKey=api_key) as service:
        res = service.cse().list(q=query, cx=cx).execute()
    return res['items'][:5]

def fetch_page_content(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            content = ' '.join([para.get_text() for para in paragraphs])
            return content
        else:
            return None
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return None

def web_search(query : str) -> str:
    return fetch_page_content(google_search(query)[0]['link'])

if __name__ == '__main__':
    #print(fetch_page_content(google_search('Group theory')[0]['link']))
    print(google_search('Group theory')[0])
