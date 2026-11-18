import html
import streamlit as st
import pandas as pd
import plotly.express as px
from data import get_country_distribution, COUNTRY_INFO, show_chart, page_title

page_title("🌍 국가별 분포")
st.caption("DB 집계 기준 (수집 전체 기간) · 공격 국가 현황")

# ---- DB 데이터 연동 및 전처리 ----
raw_df = get_country_distribution()

country_data = pd.DataFrame()
unknown_cnt = 0

if not raw_df.empty:
    try:
        cols = {c.lower(): c for c in raw_df.columns}
        c_col = cols.get('country', cols.get('국가', list(raw_df.columns)[0]))
        a_col = cols.get('attempts', cols.get('count', cols.get('공격수', list(raw_df.columns)[1])))

        temp_df = raw_df.copy()
        temp_df['norm_attempts'] = pd.to_numeric(temp_df[a_col], errors='coerce').fillna(0).astype(int)
        known = temp_df['country_code'].notna()
        unknown_cnt = int(temp_df.loc[~known, 'norm_attempts'].sum())

        df_sorted = temp_df[known].sort_values(by='norm_attempts', ascending=False).head(8).copy()

        countries_kr = []
        alphas = []
        iso2s = []

        for _, row in df_sorted.iterrows():
            code = str(row['country_code']).strip().upper()
            info = COUNTRY_INFO.get(code, {})
            en_name = row[c_col] if pd.notna(row[c_col]) else code
            countries_kr.append(info.get("kr", en_name))
            alphas.append(info.get("alpha"))
            iso2s.append(code.lower())

        country_data = pd.DataFrame({
            "국가": countries_kr,
            "iso_alpha": alphas,
            "iso2": iso2s,
            "공격 수": df_sorted['norm_attempts'].values
        })
    except Exception as e:
        print(f"Country distribution parse error: {e}")

if country_data.empty:
    st.info("표시할 국가 데이터가 없습니다.")
    st.stop()


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
    iso2 = html.escape(row["iso2"])
    rows.append(
        '<div class="rank-row">'
        f'<span class="rank-badge">{badge}</span>'
        f'<img class="rank-flag" src="https://flagcdn.com/w40/{iso2}.png" alt="{iso2.upper()}">'
        f'<span class="rank-name">{html.escape(str(row["국가"]))}</span>'
        f'<span class="rank-count">{row["공격 수"]:,}건</span>'
        '</div>'
    )

col_rank, col_map = st.columns([1, 1.4])

with col_rank:
    st.subheader("공격 국가 순위 TOP 8")
    st.markdown(RANK_CSS + "".join(rows), unsafe_allow_html=True)
    if unknown_cnt > 0:
        st.caption(f"위치 정보가 없는 세션 {unknown_cnt:,}건은 순위와 지도에서 제외했습니다.")

with col_map:
    # 1. 상단: 지도 (우측 우둘투둘한 범례 제거)
    fig_map = px.choropleth(
        country_data.dropna(subset=["iso_alpha"]),
        locations="iso_alpha",
        color="공격 수",
        hover_name="국가",
        color_continuous_scale="Reds",
        projection="natural earth",
    )
    fig_map.update_coloraxes(showscale=False)  # 범례 제거로 정돈된 느낌 부여
    fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=250)
    show_chart(fig_map, movable=True, use_container_width=True)

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
    show_chart(fig_bar, use_container_width=True)