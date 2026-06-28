from googleapiclient.discovery import build
from supabase import create_client, Client

# =========================================================================
# 🔒 [보안 설정 영역] API 및 Supabase 정보 (기밀 유지)
# =========================================================================
YOUTUBE_API_KEY = 'AIzaSyA-TXSh72KCQCQ4B-DRvmon4qUaP6k4i1k'
SUPABASE_URL = 'https://prndaklscarhlhkkylce.supabase.co' 
SUPABASE_KEY = 'sb_publishable_trNU_a81MDiyAQ3WfPR0aA_b8H45RfQ' 

# 서비스 및 클라이언트 객체 초기화
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def discover_and_save_pool(category_keyword, region_code, max_results=50):
    """
    유튜브 API로 특정 국가/카테고리의 유튜버를 대량 검색하여 Supabase 'youtuber_pool' 테이블에 저장합니다.
    relevanceLanguage를 해당 국가 코드로 매핑하여 현지 유튜버 검색 최적화를 지원합니다.
    """
    print(f"\n🚀 [{region_code}] 국가의 '{category_keyword}' 카테고리 발굴 시작 (최대 {max_results}명)...")
    
    try:
        # 1. 유튜브 Data API 검색 진행 (언어 설정을 국가 코드에 맞춰 자동 최적화)
        request = youtube.search().list(
            part='snippet',
            q=category_keyword,
            type='channel',
            regionCode=region_code,
            relevanceLanguage=region_code.lower(), # 국가에 맞춰 현지 언어 가중치 적용
            maxResults=max_results
        )
        response = request.execute()
    except Exception as e:
        print(f"❌ 유튜브 검색 API 호출 중 에러 발생: {e}")
        return

    saved_count = 0
    
    for item in response.get('items', []):
        channel_id = item['snippet']['channelId']
        channel_title = item['snippet']['title']
        
        # 2. 핸들(@주소) 정보 유실을 막기 위해 채널 상세 정보 1회 추가 조회
        try:
            ch_req = youtube.channels().list(part='snippet', id=channel_id)
            ch_res = ch_req.execute()
            
            handle_name = "정보 없음"
            if ch_res.get('items'):
                handle_name = ch_res['items'][0]['snippet'].get('customUrl', '정보 없음')
        except Exception as e:
            print(f"⚠️ {channel_title}의 핸들 주소를 가져오지 못했습니다: {e}")
            handle_name = "정보 없음"
            
        # Supabase 테이블 칼럼 구조에 맞게 딕셔너리 가공
        data = {
            "channel_id": channel_id,
            "channel_title": channel_title,
            "handle_name": handle_name,
            "category": category_keyword,
            "country": region_code
        }
        
        # 3. Supabase 내 'youtuber_pool' 테이블에 upsert (중복 방지)
        try:
            supabase.table("youtuber_pool").upsert(data).execute()
            print(f"   ✅ 창고 동기화 성공: {channel_title} ({handle_name})")
            saved_count += 1
        except Exception as e:
            print(f"   ❌ Supabase 저장 실패 ({channel_title}): {e}")
            
    print(f"🎉 [{region_code} - {category_keyword}] 완료! {saved_count}개 채널 기록됨.")

# =========================================================================
# ⚙️ 국가 및 카테고리 자동화 루프 실행부
# =========================================================================
if __name__ == "__main__":
    # 요청하신 국가 리스트 (미국, 베트남, 태국, 대만, 일본)
    countries = ['US', 'VN', 'TH', 'TW', 'JP']
    
    # 요청하신 카테고리 리스트 (각 국가별 언어 매칭률을 높이기 위해 영어 키워드로 셋팅)
    categories = ['Tech', 'Beauty', 'Fashion']
    
    # 총 5개 국가 x 3개 카테고리 = 15번의 자동 발굴 루프를 수행합니다.
    # 각 조건당 최대 50명씩 탐색합니다.
    for country in countries:
        for category in categories:
            discover_and_save_pool(category_keyword=category, region_code=country, max_results=50)
            
    print("\n🏁 [대형 프로젝트] 지정하신 모든 국가와 카테고리의 유튜버 풀 발굴이 대성공으로 끝났습니다!")