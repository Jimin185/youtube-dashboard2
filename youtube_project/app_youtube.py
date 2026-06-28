import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os

# =========================================================================
# 🔒 [설정 영역] Supabase 정보
# =========================================================================
SUPABASE_URL = 'https://prndaklscarhlhkkylce.supabase.co' 
SUPABASE_KEY = 'sb_publishable_trNU_a81MDiyAQ3WfPR0aA_b8H45RfQ' 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="글로벌 인플루언서 실적 대시보드", layout="wide")

# =========================================================================
# 📊 데이터 로드 함수
# =========================================================================
@st.cache_data(ttl=600)
def load_data():
    try:
        # 데이터 호출 후 .data로 순수 리스트만 추출하도록 안전하게 변경
        res_stats = supabase.table("channel_stats").select(
            "id, channel_id, subscriber_count, view_count, avg_views, avg_comments, engagement_rate, country, category, collected_at"
        ).execute()
        
        res_pool = supabase.table("youtuber_pool").select("channel_id, channel_title").execute()
        
        # 에러 방지를 위해 데이터 추출 구조 최적화
        stats_data = res_stats.data if hasattr(res_stats, 'data') else []
        pool_data = res_pool.data if hasattr(res_pool, 'data') else []
        
        df = pd.DataFrame(stats_data)
        pool_df = pd.DataFrame(pool_data)
        
        if df.empty:
            return pd.DataFrame()
            
        if not pool_df.empty and 'channel_id' in pool_df.columns:
            df = pd.merge(df, pool_df, on="channel_id", how="left")
            df['channel_title'] = df['channel_title'].fillna(df['channel_id'])
        else:
            df['channel_title'] = df['channel_id']
            
        return df
    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

df = load_data()

# =========================================================================
# 🖥️ UI 구성 (로고 경로 절대경로 패치 완료)
# =========================================================================
# 💡 현재 파일(app_youtube.py)이 위치한 폴더를 기준으로 로고 파일을 명확하게 찾습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(current_dir, "creatip_CI_B.png")

if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.markdown("<div style='font-size: 26px; font-weight: bold; color: #000000;'>CREATIP</div>", unsafe_allow_html=True)

st.sidebar.markdown("---") 
st.sidebar.header("🔍 데이터 필터 선택")

st.title("🌍 글로벌 인플루언서 실적 모니터링 대시보드")

if df.empty:
    st.warning("⚠️ 표시할 데이터가 없습니다.")
else:
    all_countries = ["전체"] + sorted(df['country'].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox("🗺️ 국가 선택", all_countries)
    
    all_categories = ["전체"] + sorted(df['category'].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("🏷️ 카테고리 선택", all_categories)
    
    filtered_df = df.copy()
    if selected_country != "전체":
        filtered_df = filtered_df[filtered_df['country'] == selected_country]
    if selected_category != "전체":
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
    if not filtered_df.empty and 'collected_at' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('collected_at', ascending=False).drop_duplicates('channel_id')

    # 상단 요약 카드
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 분석 대상 유튜버 수", f"{len(filtered_df)} 명")
    with col2:
        avg_subs = int(filtered_df['subscriber_count'].mean()) if not filtered_df.empty else 0
        st.metric("👥 평균 구독자 수", f"{avg_subs:,} 명")
    with col3:
        avg_eng = filtered_df['engagement_rate'].mean() if not filtered_df.empty else 0.0
        st.metric("🔥 평균 인게이지먼트 비율", f"{avg_eng:.3f} %")

    st.markdown("---")

    # 시각화 영역
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("🏆 구독자 순위 TOP 10")
        top_subs = filtered_df.sort_values('subscriber_count', ascending=False).head(10)
        if not top_subs.empty:
            fig_subs = px.bar(top_subs, x='subscriber_count', y='channel_title', orientation='h', color_continuous_scale='Blues')
            st.plotly_chart(fig_subs, use_container_width=True)

    with chart_col2:
        st.subheader("🔥 영상당 평균 조회수 TOP 10")
        top_views = filtered_df.sort_values('avg_views', ascending=False).head(10)
        if not top_views.empty:
            fig_views = px.bar(top_views, x='avg_views', y='channel_title', orientation='h', color_continuous_scale='Oranges')
            st.plotly_chart(fig_views, use_container_width=True)

    st.markdown("---")

    # 상세 데이터 표 및 단가 계산
    st.subheader("📋 인플루언서 상세 실적 및 예측 단가 현황")
    if not filtered_df.empty:
        display_df = filtered_df[['channel_title', 'country', 'category', 'subscriber_count', 'avg_views', 'avg_comments', 'engagement_rate']].copy()
        
        display_df['min_price'] = (display_df['avg_views'] * 50).fillna(0).astype(int)
        display_df['max_price'] = (display_df['avg_views'] * 100).fillna(0).astype(int)
        display_df['예측 단가 (범위)'] = display_df.apply(lambda row: f"₩{row['min_price']:,} ~ ₩{row['max_price']:,}", axis=1)
        
        display_df = display_df.drop(columns=['min_price', 'max_price'])
        display_df.columns = ['채널명', '국가', '카테고리', '구독자 수', '60일 평균 조회수', '평균 댓글수', '인게이지먼트(%)', '예측 단가 (범위)']
        display_df = display_df[['채널명', '국가', '카테고리', '구독자 수', '60일 평균 조회수', '예측 단가 (범위)', '평균 댓글수', '인게이지먼트(%)']]
        
        st.dataframe(display_df, use_container_width=True)
