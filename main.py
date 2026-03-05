import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

print("🚀 Bot process started!")

try:
    # 1. Authentication and Accessing the Google Sheet
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Load credentials from GitHub Secrets
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Open the spreadsheet (Ensure the name matches exactly!)
    sheet = client.open("Iran_Monitoring").sheet1
    print("✅ Google Sheet connected successfully!")

    # 2. Scraping News from The Guardian
    url = "https://www.theguardian.com/world/live/2026/mar/05/iran-war-latest-updates-canada-carney-trump-israel-tehran-strikes"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Targeted search for live blog blocks
    blocks = soup.select('div[id^="block-"]') 
    if not blocks:
        blocks = soup.find_all('div', class_='block')
    
    print(f"🔎 Number of news blocks found: {len(blocks)}")

    # 3. Processing and Inserting Data (Top 3 latest updates)
    if len(blocks) > 0:
        for b in blocks[:3]:
            # Extract title or the first paragraph if title is missing
            title = b.find('h2').text.strip() if b.find('h2') else "No Title (Breaking News)"
            if title == "No Title (Breaking News)" and b.find('p'):
                title = b.find('p').text.strip()[:60] + "..." 
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Insert a new row below the header (Row 2)
            sheet.insert_row([timestamp, "The Guardian", title, url], 2)
            print(f"📝 Logged to sheet: {title[:30]}...")
            
        print("🎉 All tasks completed successfully!")
    else:
        print("❓ No news content found. The URL might be expired or the site structure has changed.")

except Exception as e:
    print(f"❌ Error occurred: {e}")
