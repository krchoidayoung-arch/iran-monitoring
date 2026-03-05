import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- [Settings] Priority Keywords for IEA Monitoring ---
CRITICAL_KEYWORDS = [
    'attack', 'strike', 'blast', 'explosion', 'killed', 'casualty', 'death', 'oil',
    'school', 'drone', 'missile', 'intercepted', 'intercept', 'strike', 'airstrike',
    'tehran', 'beirut', israel', 'iran', 'saudi', 'emiraite', 'lebanon', 'oman', 'tel aviv'
    'wounded', 'injured', 'building', 'facility', 'energy', 'oil', 'nuclear', 
    'power', 'refinery', 'infrastructure', 'electricity', 'outage', 'grid', 'blackout'
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def filter_content(title, text):
    """Checks if any critical keyword exists in title or body text."""
    combined = (title + " " + text).lower()
    return any(word in combined for word in CRITICAL_KEYWORDS)

def get_guardian_live():
    print("🔎 Scanning Guardian Iran page...")
    try:
        url = "https://www.theguardian.com/world/iran"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        article = soup.select_one('a[data-link-name="article"]')
        if article:
            title = article.get_text().strip()
            link = article['href']
            if filter_content(title, ""):
                return [["The Guardian", title, link]]
    except Exception as e: print(f"⚠️ Guardian Error: {e}")
    return []

def get_bbc_middle_east():
    print("🔎 Scanning BBC Middle East...")
    try:
        url = "https://www.bbc.com/news/world/middle_east"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Find headlines in h2/h3
        articles = soup.find_all(['h2', 'h3'])[:5]
        results = []
        for a in articles:
            title = a.get_text().strip()
            link_tag = a.find_parent('a') or a.find('a')
            link = link_tag['href'] if link_tag else url
            if not link.startswith('http'): link = "https://www.bbc.com" + link
            if filter_content(title, ""):
                results.append(["BBC News", title, link])
        return results
    except Exception as e: print(f"⚠️ BBC Error: {e}")
    return []

def get_cnn_live_updates():
    # Today's specific live URL provided by Dayoung
    url = "https://edition.cnn.com/world/live-news/iran-war-us-israel-trump-03-05-26"
    print(f"🔎 Scanning CNN Live: {url}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.find_all('article') # Individual live update blocks
        results = []
        for post in posts[:10]: # Check latest 10 posts
            headline = post.find('h2')
            if headline:
                title = headline.get_text().strip()
                content = post.get_text().strip()
                if filter_content(title, content):
                    results.append(["CNN Live", title, url])
        return results
    except Exception as e: print(f"⚠️ CNN Error: {e}")
    return []

try:
    # 1. Connect to Google Sheets
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1
    print("✅ Connected to Google Sheets")

    # 2. Collect News from all sources
    all_news = get_guardian_live() + get_bbc_middle_east() + get_cnn_live_updates()
    
    # 3. Deduplication & Insertion
    existing_titles = sheet.col_values(3) # Check the "Title" column
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    added_count = 0

    for news in all_news:
        if news[1] not in existing_titles:
            # Row format: [Time, Source, Title, URL]
            sheet.insert_row([now, news[0], news[1], news[2]], 2)
            print(f"🚨 Critical Event Logged: [{news[0]}] {news[1][:40]}...")
            added_count += 1
            if added_count >= 10: break # Safety limit per run

    print(f"🎉 Task Finished. Total {added_count} new critical updates added.")

except Exception as e:
    print(f"❌ Critical System Error: {e}")
