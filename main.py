import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

def get_guardian_news():
    try:
        print("🔎 Scanning Guardian...")
        url = "https://www.theguardian.com/world/iran"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 여러 종류의 링크 태그 시도
        article = soup.select_one('a[data-link-name="article"]') or soup.find('a', class_='u-faux-block-link__overlay')
        if article:
            title = article.text.strip()
            link = article['href']
            if not link.startswith('http'): link = "https://www.theguardian.com" + link
            print(f"✅ Guardian found: {title[:20]}...")
            return ["The Guardian", title, link]
    except Exception as e:
        print(f"⚠️ Guardian Error: {e}")
    return None

def get_bbc_news():
    try:
        print("🔎 Scanning BBC...")
        url = "https://www.bbc.com/news/world/middle_east"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # BBC는 h2나 h3 안에 제목이 있는 경우가 많음
        article = soup.find('h2') or soup.find('h3')
        if article:
            title = article.text.strip()
            # 가장 가까운 링크 태그 찾기
            link_tag = article.find_parent('a') or article.find('a') or soup.select_one('a[href*="/news/world-middle-east-"]')
            link = link_tag['href'] if link_tag else url
            if not link.startswith('http'): link = "https://www.bbc.com" + link
            print(f"✅ BBC found: {title[:20]}...")
            return ["BBC News", title, link]
    except Exception as e:
        print(f"⚠️ BBC Error: {e}")
    return None

try:
    # 1. Google Sheets Connection
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1

    # 2. Collect News
    results = []
    guardian = get_guardian_news()
    if guardian: results.append(guardian)
    
    bbc = get_bbc_news()
    if bbc: results.append(bbc)

    # 3. Log to Sheet
    if not results:
        print("❓ No news found from any source today.")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for news in results:
            sheet.insert_row([now, news[0], news[1], news[2]], 2)
            print(f"📝 Added to sheet: [{news[0]}]")
        print(f"🎉 Total {len(results)} news items added!")

except Exception as e:
    print(f"❌ Critical Error: {e}")
