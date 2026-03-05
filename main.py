import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

def get_news(source_name, url, selectors):
    try:
        print(f"🔎 Scanning {source_name}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for selector in selectors:
            article = soup.select_one(selector)
            if article:
                title = article.get_text().strip()
                link = article.get('href')
                if link:
                    if not link.startswith('http'):
                        base_url = "https://www.theguardian.com" if "guardian" in url else "https://www.bbc.com" if "bbc" in url else "https://edition.cnn.com"
                        link = base_url + link
                    print(f"✅ {source_name} found: {title[:30]}...")
                    return [source_name, title, link]
    except Exception as e:
        print(f"⚠️ {source_name} Error: {e}")
    return None

try:
    # 1. Google Sheets Connection
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1

    # 2. Scrape from 3 Sources
    # We use multiple selectors to be more robust against site changes
    jobs = [
        ["The Guardian", "https://www.theguardian.com/world/iran", 
         ['a[data-link-name="article"]', 'h3 a', '.u-faux-block-link__overlay']],
        ["BBC News", "https://www.bbc.com/news/world/middle_east", 
         ['h2', 'h3', 'a[href*="/news/world-middle-east-"]']],
        ["CNN News", "https://edition.cnn.com/world/middle-east", 
         ['.container__headline', 'span.container__headline-text', 'a.container__link']]
    ]

    results = []
    for job in jobs:
        res = get_news(job[0], job[1], job[2])
        if res: results.append(res)

    # 3. Insert into Sheet
    if results:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for news in results:
            sheet.insert_row([now, news[0], news[1], news[2]], 2)
            print(f"📝 Logged to sheet: [{news[0]}]")
        print(f"🎉 Process finished! Total {len(results)} items added.")
    else:
        print("❓ No news found today. Check selectors.")

except Exception as e:
    print(f"❌ Critical Error: {e}")
