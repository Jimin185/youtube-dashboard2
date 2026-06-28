import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os

# =========================================================================
# 🔒 [설정 영역] Supabase 정보 (기밀 유지)
# =========================================================================
SUPABASE_URL = 'https://prndaklscarhlhkkylce.supabase.co' 
SUPABASE_KEY = 'sb_publishable_trNU_a81MDiyAQ3WfPR0aA_b8H45RfQ' 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🎨 Streamlit 웹페이지 기본 레이아웃 설정
st.set_page_config(page_title="글로벌 인플루언서 실적 대시보드", layout="wide")

# =========================================================================
# 📊 데이터 로드 함수 (Supabase 연동)
# =========================================================================
@st.cache_data(ttl=600)  # 10분 캐싱
def load_data():
    try:
        response = supabase.table("channel_stats").select(
            "id, channel_id, subscriber_count, view_count, avg_views, avg_comments, engagement_rate, country, category, collected_at"
        ).execute()
        
        pool_res = supabase.table("youtuber_pool").select("channel_id, channel_title").execute()
        
        pool_df = pd.DataFrame(pool_res.data) if hasattr(pool_res, 'data') else pd.DataFrame()
        df = pd.DataFrame(response.data) if hasattr(response, 'data') else pd.DataFrame()
        
        if df.empty:
            return pd.DataFrame()
            
        if not pool_df.empty:
            df = pd.merge(df, pool_df, on="channel_id", how="left")
            df['channel_title'] = df['channel_title'].fillna(df['channel_id'])
        else:
            df['channel_title'] = df['channel_id']
            
        return df
    except Exception as e:
        st.error(f"Supabase에서 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

df = load_data()

# =========================================================================
# 🖥️ 대시보드 화면 구성 (UI)
# =========================================================================

# 📌 [좌측 사이드바 영역] 로고 이미지 동적 반영
logo_path = "creatip_CI_B.png" # 💡 여기에 폴더에 넣으신 이미지 파일명을 적어주시면 됩니다!
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.markdown(
        """
        <div style="font-family: Arial; font-size: 26px; font-weight: 300; color: #000000; padding-top: 10px;">
            CREATIP
        </div>
        """, 
        unsafe_allow_html=True
    )

st.sidebar.markdown("---") 
st.sidebar.header("🔍 데이터 필터 선택")

# 메인 화면 타이틀
st.title("🌍 글로벌 인플루언서 실적 모니터링 대시보드")
st.markdown("전 세계 국가별/카테고리별 유튜버들의 최신 실적과 인게이지먼트 지표를 비교 분석합니다.")

if df.empty:
    st.warning("⚠️ 표시할 데이터가 없습니다. 창고에 데이터가 올바르게 쌓였는지 확인해 주세요.")
else:
    # 사이드바 필터 컨트롤러 연결
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

    # 📈 상단 요약 카드 (Key Metrics)
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

    # 📊 시각화 영역
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("🏆 구독자 순위 TOP 10")
        top_subs = filtered_df.sort_values('subscriber_count', ascending=False).head(10)
        if not top_subs.empty:
            fig_subs = px.bar(
                top_subs, 
                x='subscriber_count', 
                y='channel_title', 
                orientation='h',
                labels={'subscriber_count': '구독자 수', 'channel_title': '채널명'},
                color='engagement_rate',
                color_continuous_scale='Blues',
                title="구독자 수 규모 (색상 진하기: 팬들의 반응률)"
            )
            fig_subs.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_subs, use_container_width=True)
        else:
            st.info("선택하신 조건에 맞는 데이터가 존재하지 않습니다.")

    with chart_col2:
        st.subheader("🔥 영상당 평균 조회수 TOP 10")
        top_views = filtered_df.sort_values('avg_views', ascending=False).head(10)
        if not top_views.empty:
            fig_views = px.bar(
                top_views, 
                x='avg_views', 
                y='channel_title', 
                orientation='h',
                labels={'avg_views': '최근 영상 평균 조회수', 'channel_title': '채널명'},
                color='avg_views',
                color_continuous_scale='Oranges',
                title="최근 영상 10개 기준 영상 1개당 평균 조회수 화력"
            )
            fig_views.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_views, use_container_width=True)
        else:
            st.info("선택하신 조건에 맞는 데이터가 존재하지 않습니다.")

    st.markdown("---")

    # 📋 상세 데이터 표 영역
    st.subheader("📋 인플루언서 상세 실적 및 예측 단가 현황")
    
    if not filtered_df.empty:
        display_df = filtered_df[[
            'channel_title', 'country', 'category', 'subscriber_count', 'avg_views', 'avg_comments', 'engagement_rate'
        ]].copy()
        
        # 🛠️ [단가 테이블 구현] 60일 평균 조회수(avg_views)를 기반으로 최소(50원), 최대(100원) 단가를 동적 계산하여 하나의 텍스트로 결합합니다.
        display_df['min_price'] = (display_df['avg_views'] * 50).fillna(0).astype(int)
        display_df['max_price'] = (display_df['avg_views'] * 100).fillna(0).astype(int)
        
        # ₩72,982 ~ ₩109,474 포맷 생성 함수
        display_df['예측 단가 (50원~100원)'] = display_df.apply(
            lambda row: f"₩{row['min_price']:,} ~ ₩{row['max_price']:,}", axis=1
        )
        
        # 불필요해진 임시 계산용 칼럼 제거 후 최종 테이블 구성
        display_df = display_df.drop(columns=['min_price', 'max_price'])
        
        # 표 헤더 한글로 이쁘게 변경
        display_df.columns = ['채널명', '국가', '카테고리', '구독자 수', '60일 평균 조회수', '평균 댓글수', '인게이지먼트(%)', '예측 단가 (범위)']
        
        # 원래 칼럼 순서 재배치 (예측 단가를 평균 조회수 바로 옆에 배치하여 가독성 상향)
        display_df = display_df[['채널명', '국가', '카테고리', '구독자 수', '60일 평균 조회수', '예측 단가 (범위)', '평균 댓글수', '인게이지먼트(%)']]
        
        st.dataframe(
            display_df.style.format({
                '구독자 수': '{:,}',
                '60일 평균 조회수': '{:,}',
                '평균 댓글수': '{:,}',
                '인게이지먼트(%)': '{:.3f}%'
            }), 
            use_container_width=True
        )
    else:
        st.info("데이터 표를 구성할 항목이 없습니다.")