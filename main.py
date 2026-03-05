import os, json, gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

print("🚀 [TEST] Checking connection...")

try:
    # 1. Google Sheets Connection
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Open sheet (Check if the name matches 'Iran_Monitoring' exactly!)
    sheet = client.open("Iran_Monitoring").sheet1
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Try writing a simple test row
    sheet.insert_row([now, "TEST", "The robot is successfully connected!", "Paris-Test"], 2)
    
    print(f"✅ [SUCCESS] Check your Google Sheet now! ({now})")

except Exception as e:
    print(f"❌ [ERROR] Something went wrong: {e}")
