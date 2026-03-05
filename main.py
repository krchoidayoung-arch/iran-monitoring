import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

print("--- [BOT] STARTING IRAN NEWS MONITOR ---")

try:
    # 1. Google Sheets Connection
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1
    print("--- [BOT] CONNECTED TO GOOGLE SHEETS ✅ ---")

    # 2. Find Today's Latest Iran News Automatically
    search_url = "https://www.theguardian.com/world/iran"
    headers = {'User-Agent': 'Mozilla/5.0'}
    search_res = requests.get(search_url, headers=headers)
    search_soup = BeautifulSoup(search_res.text, 'html.parser')
    
    # Get the very first article link on the page
    latest_article = search_soup.select_one('a[data-link-name="article"]')
    
    if latest_article:
        news_url = latest_article['href']
        if not news_url.startswith('http'):
            news_url = "https://www.theguardian.com" + news_url
        print(f"--- [BOT] FOUND LATEST NEWS URL: {news_url} ---")
        
        # 3. Scrape the content
        news_res = requests.get(news_url, headers=headers)
        news_soup = BeautifulSoup(news_res.text, 'html.parser')
        title = news_soup.find('h1').text.strip() if news_soup.find('h1') else "Latest Iran News Update"
        
        # Write to sheet
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.insert_row([now, "The Guardian", title, news_url], 2)
        print(f"--- [BOT] SUCCESS! LOGGED: {title[:40]}... ---")
    else:
        print("--- [BOT] FAILED TO FIND NEWS ARTICLES ON THE PAGE ---")

except Exception as e:
    print(f"--- [BOT] ERROR OCCURRED: {str(e)} ---")
