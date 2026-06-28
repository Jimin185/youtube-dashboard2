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

def get_recent_video_stats(channel_id, max_videos=10):
    """채널의 최근 동영상 10개를 분석하여 평균 조회수, 평균 댓글수, 인게이지먼트를 계산합니다."""
    try:
        # 채널의 업로드 재생목록 ID 및 구독자수 가져오기
        ch_res = youtube.channels().list(part='contentDetails,statistics', id=channel_id).execute()
        if not ch_res.get('items'):
            return 0, 0, 0, 0, 0
            
        item = ch_res['items'][0]
        subscribers = int(item['statistics'].get('subscriberCount', 0))
        total_views = int(item['statistics'].get('viewCount', 0))
        uploads_playlist_id = item['contentDetails']['relatedPlaylists']['uploads']
        
        # 최근 동영상 목록 가져오기
        playlist_res = youtube.playlistItems().list(part='snippet', playlistId=uploads_playlist_id, maxResults=max_videos).execute()
        video_ids = [v['snippet']['resourceId']['videoId'] for v in playlist_res.get('items', [])]
        
        if not video_ids:
            return subscribers, total_views, 0, 0, 0
            
        # 동영상 세부 통계 가져오기
        video_res = youtube.videos().list(part='statistics', id=','.join(video_ids)).execute()
        
        total_recent_views = 0
        total_recent_comments = 0
        for v_item in video_res.get('items', []):
            stats = v_item['statistics']
            total_recent_views += int(stats.get('viewCount', 0))
            total_recent_comments += int(stats.get('commentCount', 0))
            
        actual_count = len(video_ids)
        avg_views = int(total_recent_views / actual_count)
        avg_comments = int(total_recent_comments / actual_count)
        engagement_rate = round((avg_comments / subscribers) * 100, 3) if subscribers > 0 else 0
        
        return subscribers, total_views, avg_views, avg_comments, engagement_rate
    except Exception as e:
        print(f"⚠️ API 데이터 가공 중 에러 발생: {e}")
        return None

def collect_and_save_metrics():
    """Supabase 풀에서 유튜버 목록을 읽을 때 국가/카테고리도 함께 가져와 실적 창고에 기록합니다. (2주에 한 번 실행용)"""
    print("\n📈 [2주 주기] 국가별/카테고리별 유튜버 실적 지표 추적을 시작합니다...")
    
    # 1. Supabase 'youtuber_pool'에서 등록된 유튜버 정보(국가, 카테고리 포함) 전부 읽어오기
    try:
        pool_res = supabase.table("youtuber_pool").select("channel_id, channel_title, country, category").execute()
        youtubers = pool_res.data
    except Exception as e:
        print(f"❌ Supabase 풀 목록 읽기 실패: {e}")
        return
        
    if not youtubers:
        print("ℹ️ 풀에 등록된 유튜버가 없습니다. 1단계 발굴 코드를 먼저 돌려주세요.")
        return
        
    print(f"📋 창고 분석 결과: 총 {len(youtubers)}명의 유튜버 실적을 추적합니다.")
    
    # 2. 루프를 돌며 유튜버별 실적 계산 및 누적창고 저장
    success_count = 0
    for y in youtubers:
        c_id = y['channel_id']
        c_title = y['channel_title']
        c_country = y['country']    
        c_category = y['category']  
        
        print(f"⏳ 실적 측정 중... -> {c_title} [{c_country} / {c_category}]")
        
        # 유튜브 API 기반 심층 지표 추출
        metrics = get_recent_video_stats(c_id)
        if not metrics:
            continue
            
        subs, t_views, a_views, a_comments, e_rate = metrics
        
        # 'channel_stats' 테이블 칼럼 구조에 맞게 데이터 세팅
        stats_data = {
            "channel_id": c_id,
            "subscriber_count": subs,
            "view_count": t_views,
            "avg_views": a_views,
            "avg_comments": a_comments,
            "engagement_rate": e_rate,
            "country": c_country,     
            "category": c_category     
        }
        
        # Supabase 누적 창고에 insert
        try:
            supabase.table("channel_stats").insert(stats_data).execute()
            print(f"   📊 스냅샷 저장 완료 -> 구독자: {subs:,}명 | 인게이지: {e_rate}% | 국가: {c_country}")
            success_count += 1
        except Exception as e:
            print(f"   ❌ 실적 저장 실패 ({c_title}): {e}")
            
    print(f"\n🎉 실적 기록 종료! 총 {success_count}개 채널의 실적 데이터가 국가별로 안전하게 보관되었습니다.")

if __name__ == "__main__":
    collect_and_save_metrics()