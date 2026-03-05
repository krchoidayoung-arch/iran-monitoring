import os, json, gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

print("🚀 TEST START: Checking connection...")

try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # 엑셀 시트 이름이 'Iran_Monitoring'이 맞는지 꼭 확인하세요!
    sheet = client.open("Iran_Monitoring").sheet1
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 테스트 문구를 엑셀에 써봅니다.
    sheet.insert_row([now, "TEST", "The robot is alive!", "Success"], 2)
    
    print(f"✅ SUCCESS: Check your Google Sheet at {now}")

except Exception as e:
    print(f"❌ ERROR: {e}")
