import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 인증 및 시트 열기
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(json.loads(os.environ["GSPREAD_CREDENTIALS"]), scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open("Iran_Monitoring").sheet1

# 2. 가디언 뉴스 긁기
url = "https://www.theguardian.com/world/live/2026/mar/05/iran-war-latest-updates-canada-carney-trump-israel-tehran-strikes"
soup = BeautifulSoup(requests.get(url).text, 'html.parser')
blocks = soup.find_all('div', class_='block')

# 3. 데이터 추가 (최신 3개)
for b in blocks[:3]:
    title = b.find('h2').text.strip() if b.find('h2') else "No Title"
    sheet.insert_row([datetime.now().strftime("%Y-%m-%d %H:%M"), "The Guardian", title, url], 2)
