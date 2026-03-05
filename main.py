import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- [정밀 분석 사전] ---
ME_COUNTRIES = ['israel', 'iran', 'lebanon', 'saudi', 'yemen', 'syria', 'iraq', 'jordan', 'egypt', 'turkey', 'qatar', 'uae']
ME_CITIES = ['tehran', 'beirut', 'tel aviv', 'haifa', 'gaza', 'isfahan', 'damascus', 'baghdad', 'erbil', 'sanaa', 'hodeidah', 'dahieh']
EXCLUDE_KEYWORDS = ['russia', 'ukraine', 'putin', 'zelensky', 'moscow', 'kyiv'] # 러시아 관련 제외

METHODS = {
    'Missile': ['missile', 'ballistic', 'cruise', 'rocket'],
    'Drone': ['drone', 'uav', 'kamikaze', 'shahed'],
    'Submarine/Vessel': ['submarine', 'warship', 'vessel', 'navy', 'ship'],
    'Airstrike': ['airstrike', 'bombing', 'jet', 'fighter', 'warplane'],
    'Cyber': ['cyber', 'hacking', 'network']
}

ENERGY_KEYWORDS = ['oil', 'refinery', 'storage', 'terminal', 'pipeline', 'power plant', 'grid', 'blackout', 'substation', 'electricity']

def analyze_incident(title, content):
    text = (title + " " + content).lower()
    
    # 1. 제외 키워드 체크 (러시아 등)
    if any(ex in text for ex in EXCLUDE_KEYWORDS):
        return None

    # 2. 공격 수단 추출
    found_method = "Unknown"
    for key, synonyms in METHODS.items():
        if any(s in text for s in synonyms):
            found_method = key
            break
            
    # 3. 피해국 & 공격국 추론
    victim = "Middle East"
    attacker = "Unknown"
    found_city = "Unknown"
    
    for city in ME_CITIES:
        if city in text:
            found_city = city.capitalize()
            break
    
    # 기초적인 주체 추론
    if 'israel' in text and ('iran' in text or 'lebanon' in text or 'hezbollah' in text):
        attacker, victim = "Israel", "Iran/Lebanon"
    elif 'iran' in text and 'israel' in text:
        attacker, victim = "Iran", "Israel"
    elif 'houthi' in text or 'yemen' in text:
        attacker, victim = "Houthi", "Vessel/Saudi"

    # 4. 에너지 시설 강조 요약
    is_energy = any(e in text for e in ENERGY_KEYWORDS)
    energy_prefix = "⚠️ [ENERGY HIT] " if is_energy else ""
    summary = energy_prefix + content[:150].replace('\n', ' ') + "..."
    
    return [victim, found_city, attacker, found_method, summary]

def scrape_source(name, url, headers):
    print(f"🔎 Scanning {name}...")
    try:
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 각 매체별 포스트 추출 로직 (가장 넓은 범위)
        if name == "CNN":
            blocks = soup.find_all('article')
        elif name == "Guardian":
            blocks = soup.select('div[id^="block-"]') or soup.find_all('article')
        else: # BBC
            blocks = soup.select('div[data-testid="curated-article-card"]') or soup.find_all(['h2', 'h3'])
            
        data_list = []
        for b in blocks[:15]: # 매체별 최신 15개 포스트 확인
            title = b.get_text().strip()[:100]
            content = b.get_text().strip()
            time_tag = b.find('time') or b.find('span', class_='sc-')
            article_time = time_tag.get_text().strip() if time_tag else "Live"
            
            analysis = analyze_incident(title, content)
            if analysis: # 중동 관련이고 분석이 된 경우만 추가
                data_list.append([article_time, name, title] + analysis + [url])
        return data_list
    except Exception as e:
        print(f"⚠️ {name} Error: {e}"); return []

try:
    # 1. 시트 인증 및 연결
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1

    # 2. 3대 매체 통합 수집
    headers = {'User-Agent': 'Mozilla/5.0'}
    sources = [
        ["CNN", "https://edition.cnn.com/world/live-news/iran-war-us-israel-trump-03-05-26"],
        ["Guardian", "https://www.theguardian.com/world/iran"],
        ["BBC", "https://www.bbc.com/news/world/middle_east"]
    ]

    combined_data = []
    for src in sources:
        combined_data.extend(scrape_source(src[0], src[1], headers))

    # 3. 중복 제거 및 데이터 기록
    # 시트의 G열(Comment/요약) 내용을 가져와 중복 체크 (제목보다 요약이 더 확실함)
    existing_summaries = sheet.col_values(7)
    bot_run_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    added_count = 0
    for data in combined_data:
        # data: [article_time, source, title, victim, city, attacker, method, summary, link]
        if data[7] not in existing_summaries:
            # 최종 행 구성: 실행시간, 기사시점, 피해국, 도시, 공격국, 수단, 요약, 링크
            row = [bot_run_time, data[0], data[3], data[4], data[5], data[6], data[7], data[8]]
            sheet.insert_row(row, 2)
            added_count += 1
            if added_count >= 25: break # 과부하 방지

    print(f"🎉 Success! {added_count} Middle East priority events logged to your monitor.")

except Exception as e:
    print(f"❌ System Error: {e}")
