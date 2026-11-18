import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.data import get_country_distribution

st.title("🌍 국가별 분포")
st.caption("실시간 DB 집계 기준 · 공격 국가 현황")

# ---- DB 데이터 연동 및 전처리 ----
raw_df = get_country_distribution()

ISO_MAP = {
    "United States": {"alpha": "USA", "iso2": "us", "kr": "미국"},
    "China": {"alpha": "CHN", "iso2": "cn", "kr": "중국"},
    "Russia": {"alpha": "RUS", "iso2": "ru", "kr": "러시아"},
    "Vietnam": {"alpha": "VNM", "iso2": "vn", "kr": "베트남"},
    "Brazil": {"alpha": "BRA", "iso2": "br", "kr": "브라질"},
    "India": {"alpha": "IND", "iso2": "in", "kr": "인도"},
    "Germany": {"alpha": "DEU", "iso2": "de", "kr": "독일"},
    "Ukraine": {"alpha": "UKR", "iso2": "ua", "kr": "우크라이나"},
    "South Korea": {"alpha": "KOR", "iso2": "kr", "kr": "대한민국"},
    "Korea": {"alpha": "KOR", "iso2": "kr", "kr": "대한민국"},
    "France": {"alpha": "FRA", "iso2": "fr", "kr": "프랑스"},
    "Iran": {"alpha": "IRN", "iso2": "ir", "kr": "이란"},
    "Sweden": {"alpha": "SWE", "iso2": "se", "kr": "스웨덴"}
}

country_data = pd.DataFrame()

if not raw_df.empty:
    try:
        cols = {c.lower(): c for c in raw_df.columns}
        c_col = cols.get('country', cols.get('국가', list(raw_df.columns)[0]))
        a_col = cols.get('attempts', cols.get('count', cols.get('공격수', list(raw_df.columns)[1])))

        temp_df = raw_df.copy()
        temp_df['norm_country'] = temp_df[c_col].astype(str).str.strip()
        temp_df['norm_attempts'] = pd.to_numeric(temp_df[a_col], errors='coerce').fillna(0)

        df_sorted = temp_df.sort_values(by='norm_attempts', ascending=False).head(8).copy()
        
        countries_kr = []
        alphas = []
        iso2s = []
        
        for _, row in df_sorted.iterrows():
            c_name = row['norm_country']
            info = ISO_MAP.get(c_name, {"alpha": "USA", "iso2": "us", "kr": c_name})
            countries_kr.append(info["kr"])
            alphas.append(info["alpha"])
            iso2s.append(info["iso2"])
            
        country_data = pd.DataFrame({
            "국가": countries_kr,
            "iso_alpha": alphas,
            "iso2": iso2s,
            "공격 수": df_sorted['norm_attempts'].values
        })
    except Exception as e:
        print(f"Country distribution parse error: {e}")

if country_data.empty:
    country_data = pd.DataFrame({
        "국가": ["러시아", "중국", "미국", "베트남", "브라질", "인도", "독일", "우크라이나"],
        "iso_alpha": ["RUS", "CHN", "USA", "VNM", "BRA", "IND", "DEU", "UKR"],
        "iso2": ["ru", "cn", "us", "vn", "br", "in", "de", "ua"],
        "공격 수": [924, 781, 612, 398, 301, 264, 187, 142],
    }).sort_values("공격 수", ascending=False).reset_index(drop=True)


# ---- 2열 균형 레이아웃: 좌측(TOP 8 순위) / 우측(지도 + 가로 콤팩트 막대) ----
RANK_CSS = """<style>
.rank-row{display:flex;align-items:center;gap:10px;padding:8px 4px;border-bottom:1px solid rgba(128,128,128,.15);font-size:14px;}
.rank-badge{width:24px;text-align:center;font-size:16px;}
.rank-num{display:inline-block;width:20px;height:20px;line-height:20px;border-radius:50%;background:#C5CCD6;color:#fff;font-size:11px;font-weight:600;text-align:center;}
.rank-flag{width:24px;height:auto;border-radius:2px;box-shadow:0 0 0 1px rgba(128,128,128,.3);}
.rank-name{flex:1;}
.rank-count{font-variant-numeric:tabular-nums;font-weight:600;}
</style>"""

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

rows = []
for rank, (_, row) in enumerate(country_data.iterrows(), start=1):
    badge = MEDALS.get(rank, f'<span class="rank-num">{rank}</span>')
    rows.append(
        '<div class="rank-row">'
        f'<span class="rank-badge">{badge}</span>'
        f'<img class="rank-flag" src="https://flagcdn.com/w40/{row["iso2"]}.png" alt="{row["iso2"].upper()}">'
        f'<span class="rank-name">{row["국가"]}</span>'
        f'<span class="rank-count">{row["공격 수"]:,}건</span>'
        '</div>'
    )

col_rank, col_map = st.columns([1, 1.4])

with col_rank:
    st.subheader("공격 국가 순위 TOP 8")
    st.markdown(RANK_CSS + "".join(rows), unsafe_allow_html=True)

with col_map:
    # 1. 상단: 지도 (우측 우둘투둘한 범례 제거)
    fig_map = px.choropleth(
        country_data,
        locations="iso_alpha",
        color="공격 수",
        hover_name="국가",
        color_continuous_scale="Reds",
        projection="natural earth",
    )
    fig_map.update_coloraxes(showscale=False)  # 범례 제거로 정돈된 느낌 부여
    fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=250)
    st.plotly_chart(fig_map, use_container_width=True)

    # 2. 하단: 지도 직하단에 들어가는 가로 막대 그래프 (정돈된 시각화)
    fig_bar = px.bar(
        country_data.sort_values("공격 수", ascending=True),
        x="공격 수", y="국가", orientation="h",
        color="공격 수", color_continuous_scale="Reds",
        text_auto=True,
    )
    fig_bar.update_xaxes(visible=False)  # 눈금선 제거
    fig_bar.update_yaxes(title=None, tickfont=dict(size=12))
    fig_bar.update_traces(textposition="outside", cliponaxis=False, textfont=dict(size=11))
    fig_bar.update_coloraxes(showscale=False)
    fig_bar.update_layout(height=230, margin=dict(t=10, b=0, l=0, r=40))
    st.plotly_chart(fig_bar, use_container_width=True)