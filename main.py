import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- [Settings] Priority Keywords & Locations for IEA Monitoring ---
CRITICAL_KEYWORDS = [
    'attack', 'strike', 'blast', 'explosion', 'killed', 'casualty', 'death', 
    'wounded', 'injured', 'building', 'facility', 'energy', 'oil', 'nuclear', 
    'power', 'refinery', 'infrastructure', 'electricity', 'outage', 'grid', 'blackout',
    'tehran', 'beirut', 'israel', 'iran', 'saudi', 'emirate', 'lebanon', 'oman', 'tel aviv'
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def filter_content(title, text):
    combined = (title + " " + text).lower()
    return any(word in combined for word in CRITICAL_KEYWORDS)

def get_guardian_live():
    print("🔎 Scanning Guardian Iran page...")
    try:
        url = "https://www.theguardian.com/world/iran"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        blocks = soup.select('div[id^="block-"]') or soup.find_all('article')
        for b in blocks[:5]:
            title = b.find('h2').get_text().strip() if b.find('h2') else "Breaking Update"
            link_tag = b.find('a', class_='block-share__item--twitter')
            link = link_tag['href'] if link_tag else url
            time_tag = b.find('time')
            article_time = time_tag.get_text().strip() if time_tag else "Unknown Time"
            if filter_content(title, b.get_text()):
                results.append(["The Guardian", article_time, title, link])
        return results
    except Exception as e: print(f"⚠️ Guardian Error: {e}"); return []

def get_bbc_middle_east():
    print("🔎 Scanning BBC Middle East...")
    try:
        url = "https://www.bbc.com/news/world/middle_east"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        articles = soup.select('div[data-testid="curated-article-card"]') or soup.find_all(['h2', 'h3'])[:5]
        for a in articles:
            headline = a.find(['h2', 'h3']) or a
            title = headline.get_text().strip()
            link_tag = a.find_parent('a') or a.find('a')
            link = link_tag['href'] if link_tag else url
            if not link.startswith('http'): link = "https://www.bbc.com" + link
            time_tag = a.find('span', {'data-testid': 'card-metadata-lastupdated'}) or a.find('time')
            article_time = time_tag.get_text().strip() if time_tag else "Recent"
            if filter_content(title, ""):
                results.append(["BBC News", article_time, title, link])
        return results
    except Exception as e: print(f"⚠️ BBC Error: {e}"); return []

def get_cnn_live_updates():
    url = "https://edition.cnn.com/world/live-news/iran-war-us-israel-trump-03-05-26"
    print(f"🔎 Scanning CNN Live: {url}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.find_all('article')
        results = []
        for post in posts[:10]:
            headline = post.find('h2')
            if headline:
                title = headline.get_text().strip()
                time_tag = post.find('span', class_='sc-') or post.find('time')
                article_time = time_tag.get_text().strip() if time_tag else "Live"
                if filter_content(title, post.get_text()):
                    results.append(["CNN Live", article_time, title, url])
        return results
    except Exception as e: print(f"⚠️ CNN Error: {e}"); return []

try:
    # 1. Google Sheets Auth
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1

    # 2. Collect News
    all_news = get_guardian_live() + get_bbc_middle_east() + get_cnn_live_updates()
    
    # 3. Deduplication (By checking the Title column in the sheet)
    existing_titles = sheet.col_values(4) # Title is in Column D
    bot_run_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    added_count = 0

    for news in all_news:
        source, article_time, title, link = news
        if title not in existing_titles:
            # Format: [Bot Run Time, Article Post Time, Source, Title, Link]
            sheet.insert_row([bot_run_time, article_time, source, title, link], 2)
            print(f"🚨 New Critical Update Logged: [{source}] {title[:30]}")
            added_count += 1
            if added_count >= 10: break

    print(f"🎉 Success! {added_count} new items added to your IEA Monitor.")

except Exception as e:
    print(f"❌ Error: {e}")
