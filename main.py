import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

def get_guardian_news():
    print("🔎 Fetching Guardian News...")
    url = "https://www.theguardian.com/world/iran"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    article = soup.select_one('a[data-link-name="article"]')
    if article:
        title = article.text.strip()
        link = article['href']
        if not link.startswith('http'): link = "https://www.theguardian.com" + link
        return ["The Guardian", title, link]
    return None

def get_bbc_news():
    print("🔎 Fetching BBC News...")
    url = "https://www.bbc.com/news/world/middle_east"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    # BBC의 최신 뉴스 헤드라인 구조 대응
    article = soup.find('h2') or soup.find('h3')
    if article:
        title = article.text.strip()
        link_tag = article.find_parent('a') or article.find('a')
        link = link_tag['href'] if link_tag else url
        if not link.startswith('http'): link = "https://www.bbc.com" + link
        return ["BBC News", title, link]
    return None

try:
    # 1. 시트 연결
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1

    # 2. 뉴스 수집
    news_list = [get_guardian_news(), get_bbc_news()]
    
    # 3. 데이터 입력
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for news in news_list:
        if news:
            sheet.insert_row([now, news[0], news[1], news[2]], 2)
            print(f"✅ Logged: [{news[0]}] {news[1][:30]}...")

    print("🎉 All news monitoring tasks completed!")

except Exception as e:
    print(f"❌ ERROR: {e}")
