import os, json, gspread, requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- [설정] 핵심 키워드 (다영님의 에너지 모니터링 최적화) ---
CRITICAL_KEYWORDS = [
    'oil', 'refinery', 'storage', 'terminal', 'pipeline', 'power', 'grid', 'blackout', 
    'infrastructure', 'attack', 'strike', 'missile', 'drone', 'uav', 'submarine', 
    'explosion', 'building', 'killed', 'casualty', 'tehran', 'beirut', 'israel'
]
EXCLUDE_KEYWORDS = ['russia', 'ukraine', 'putin', 'moscow']

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def analyze_incident(title, content):
    text = (title + " " + content).lower()
    if any(ex in text for ex in EXCLUDE_KEYWORDS): return None
    
    # 공격 수단 및 피해국 추론 (기존 로직 유지)
    method = "Unknown"
    for m in ['missile', 'drone', 'submarine', 'airstrike']:
        if m in text: method = m.capitalize(); break
    
    victim, attacker, city = "Middle East", "Unknown", "Unknown"
    if 'israel' in text and ('iran' in text or 'lebanon' in text): attacker, victim = "Israel", "Iran/Lebanon"
    elif 'iran' in text and 'israel' in text: attacker, victim = "Iran", "Israel"
    
    # 에너지 관련 특별 요약
    prefix = "⚠️ [ENERGY] " if any(e in text for e in ['oil', 'power', 'refinery', 'grid']) else ""
    return [victim, city, attacker, method, prefix + content[:150].strip() + "..."]

def get_guardian_live():
    print("🔎 Scanning Guardian (Aggressive Search)...")
    try:
        url = "https://www.theguardian.com/world/iran"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        
        # 가디언의 다양한 블록 형태(id 기반, article 태그 기반 등)를 모두 찾습니다.
        blocks = soup.select('div[id^="block-"]') or soup.find_all('article') or soup.select('.dcr-16986os')
        
        for b in blocks[:12]:
            block_id = b.get('id') or b.get('data-block-id')
            direct_link = f"{url}#{block_id}" if block_id else url
            
            # 제목 찾기 (h2, h3 혹은 첫 번째 p 태그)
            title_tag = b.find(['h2', 'h3'])
            title = title_tag.get_text().strip() if title_tag else "Guardian Update"
            
            # 본문 및 시간 추출
            content = b.get_text().strip()
            time_tag = b.find('time')
            article_time = time_tag.get_text().strip() if time_tag else "Recent"
            
            # 제목이 기본값인 경우 본문 앞부분으로 대체
            if title == "Guardian Update" and len(content) > 30:
                title = content[:50].replace('\n', ' ') + "..."

            analysis = analyze_incident(title, content)
            if analysis:
                # 결과: [시점, 출처, 제목, 피해국, 지명, 공격국, 수단, 요약, 링크]
                results.append([article_time, "Guardian", title] + analysis + [direct_link])
        return results
    except Exception as e: print(f"⚠️ Guardian Error: {e}"); return []

# (CNN, BBC 로직은 기존과 동일하게 유지하여 combined_data에 추가)
# ... (기존 CNN, BBC 함수들)

def get_bbc_middle_east():
    # BBC 로직 (생략되었으나 전체 코드에 포함됨)
    try:
        url = "https://www.bbc.com/news/world/middle_east"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []
        articles = soup.select('div[data-testid="curated-article-card"]') or soup.find_all(['h2', 'h3'])
        for a in articles[:8]:
            title = a.get_text().strip()
            link_tag = a.find_parent('a') or a.find('a')
            link = link_tag['href'] if link_tag else url
            if not link.startswith('http'): link = "https://www.bbc.com" + link
            time_tag = a.find('time') or a.find('span', {'data-testid': 'card-metadata-lastupdated'})
            article_time = time_tag.get_text().strip() if time_tag else "Recent"
            analysis = analyze_incident(title, "")
            if analysis: results.append([article_time, "BBC News", title] + analysis + [link])
        return results
    except: return []

def get_cnn_live_updates():
    # CNN 로직 (생략되었으나 전체 코드에 포함됨)
    try:
        url = "https://edition.cnn.com/world/live-news/iran-war-us-israel-trump-03-05-26"
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.find_all('article')
        results = []
        for post in posts[:10]:
            post_id = post.get('id')
            direct_link = f"{url}#{post_id}" if post_id else url
            headline = post.find('h2')
            if headline:
                title = headline.get_text().strip()
                content = post.get_text().strip()
                time_tag = post.find('time') or post.find('span', class_='sc-')
                article_time = time_tag.get_text().strip() if time_tag else "Live"
                analysis = analyze_incident(title, content)
                if analysis: results.append([article_time, "CNN Live", title] + analysis + [direct_link])
        return results
    except: return []

try:
    # 1. 시트 연결
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GSPREAD_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Iran_Monitoring").sheet1

    # 2. 3대 매체 통합 수집
    all_news = get_guardian_live() + get_bbc_middle_east() + get_cnn_live_updates()
    
    # 3. 중복 제거 (제목 기준) 및 입력
    existing_titles = sheet.col_values(3) # C열(Title) 기준
    bot_run_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    added_count = 0
    for data in all_news:
        # data format: [article_time, source, title, victim, city, attacker, method, summary, link]
        if data[2] not in existing_titles:
            # 최종 행: 실행시간(A), 기사시점(B), 출처(X-삭제가능), 피해국(C), 지명(D), 공격국(E), 수단(F), 요약(G), 링크(H)
            # 다영님의 칼럼 순서에 맞춰 재배치: [실행시간, 기사시점, 피해국, 지명, 공격국, 수단, 요약, 링크]
            row = [bot_run_time, data[0], data[3], data[4], data[5], data[6], data[7], data[8]]
            sheet.insert_row(row, 2)
            added_count += 1
            if added_count >= 20: break

    print(f"🎉 Success! {added_count} items (including The Guardian) added.")

except Exception as e:
    print(f"❌ Error: {e}")
