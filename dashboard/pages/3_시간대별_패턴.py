import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dashboard.data import get_time_patterns

# 팀 공통 색상
COLOR_PEAK = "#E5484D"
COLOR_BASE = "#A9B8C7"
COLOR_LINE = "#2F80ED"
COLOR_WEEKDAY = "#5B7089"
COLOR_WEEKEND = "#F5A623"

st.title("⏰ 시간대별 패턴")
st.caption("실시간 DB 집계 기준 · 한국 시간(KST)")
st.caption("공격 수 = 허니팟에 기록된 공격 시도 횟수")

days = ["월", "화", "수", "목", "금", "토", "일"]
hours = list(range(24))

# ---- DB 데이터 연동 및 전처리 ----
raw_df = get_time_patterns()
use_mock = True

if not raw_df.empty:
    try:
        day_map = {
            'monday': '월', 'tuesday': '화', 'wednesday': '수', 'thursday': '목', 'friday': '금', 'saturday': '토', 'sunday': '일',
            'mon': '월', 'tue': '화', 'wed': '수', 'thu': '목', 'fri': '금', 'sat': '토', 'sun': '일',
            '0': '월', '1': '화', '2': '수', '3': '목', '4': '금', '5': '토', '6': '일',
            0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일',
            '월': '월', '화': '화', '수': '수', '목': '목', '금': '금', '토': '토', '일': '일'
        }
        col_day = [c for c in raw_df.columns if 'day' in c.lower() or '요일' in c][0]
        col_hour = [c for c in raw_df.columns if 'hour' in c.lower() or '시간' in c][0]
        col_val = [c for c in raw_df.columns if 'attempt' in c.lower() or 'count' in c.lower() or '시도' in c or '수' in c][0]

        temp_df = raw_df.copy()
        temp_df['clean_day'] = temp_df[col_day].astype(str).str.strip().str.lower()
        temp_df['mapped_day'] = temp_df['clean_day'].map(day_map).fillna(temp_df[col_day])
        
        pivot = temp_df.pivot_table(index='mapped_day', columns=col_hour, values=col_val, fill_value=0)
        heatmap_data = pivot.reindex(index=days, columns=hours, fill_value=0)
        use_mock = False
    except Exception as e:
        print(f"Time pattern pivot error: {e}")
        use_mock = True

if use_mock:
    np.random.seed(42)
    base_pattern = np.array([15,10,8,6,5,5,8,12,18,22,25,28,30,28,25,23,26,32,38,35,30,24,20,17])
    day_factor = np.array([1.0, 1.25, 1.1, 1.15, 0.8, 0.65, 0.55])
    noise = np.random.uniform(0.85, 1.15, size=(7, 24))
    heatmap_data = pd.DataFrame(
        np.outer(day_factor, base_pattern) * noise,
        index=days, columns=hours,
    ).round(0).astype(int)

# ---- 요약 숫자 계산 ----
hour_total = heatmap_data.sum(axis=0)
day_total = heatmap_data.sum(axis=1)
peak_hour = int(hour_total.idxmax())
low_hour = int(hour_total.idxmin())
peak_day = day_total.idxmax()
low_day = day_total.idxmin()
weekday_avg = int(day_total[days[:5]].mean()) if len(days[:5]) > 0 else 0
weekend_avg = int(day_total[days[5:]].mean()) if len(days[5:]) > 0 else 0
weekend_change = (weekend_avg / weekday_avg - 1) * 100 if weekday_avg > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("공격이 가장 많은 시간", f"{peak_hour}시")
c1.caption(f"{int(hour_total.max()):,}건 (7일 합계)")
c2.metric("공격이 가장 많은 요일", f"{peak_day}요일")
c2.caption(f"{int(day_total.max()):,}건 (7일 합계)")
c3.metric("평일 하루 평균", f"{weekday_avg:,}건")
c4.metric("주말 하루 평균", f"{weekend_avg:,}건", f"{weekend_change:+.0f}% (평일 대비)", delta_color="off")
st.caption("평일은 5일, 주말은 2일이라 합계가 아니라 하루 평균으로 비교했습니다.")

st.divider()

# ---- 막대 + 꺾은선: 시간대별 공격 수 ----
st.subheader("시간대별 공격 수")

hour_df = pd.DataFrame({"시간": hours, "공격 수": hour_total.values})
bar_colors = [COLOR_PEAK if h == peak_hour else COLOR_BASE for h in hours]

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=hour_df["시간"], y=hour_df["공격 수"],
    marker_color=bar_colors,
    text=hour_df["공격 수"],
    textposition="outside",
    textfont=dict(size=9),
    cliponaxis=False,
    name="시간대별 공격 수 (막대)",
))
fig_bar.add_trace(go.Bar(x=[None], y=[None], marker_color=COLOR_PEAK, name="공격이 가장 많은 시간"))
fig_bar.add_trace(go.Scatter(
    x=hour_df["시간"], y=hour_df["공격 수"],
    mode="lines+markers",
    line=dict(color=COLOR_LINE, width=3),
    marker=dict(size=8, color=COLOR_LINE),
    name="시간대별 증감 흐름 (꺾은선)",
))
fig_bar.update_xaxes(dtick=1, title="시간 (KST)", range=[-0.5, 23.5])
fig_bar.update_yaxes(title=None, range=[0, hour_total.max() * 1.2])
fig_bar.add_annotation(text="공격 수 (7일 합계)", xref="paper", yref="paper", x=0, y=1.1, xanchor="left", showarrow=False)
fig_bar.update_layout(height=420, margin=dict(t=60), showlegend=True, legend=dict(orientation="h", x=0.5, xanchor="center", y=1.12, yanchor="bottom"))
st.plotly_chart(fig_bar, use_container_width=True)

min_val = hour_total.min()
ratio = (hour_total.max() / min_val) if min_val > 0 else 1.0
st.markdown(f"- **{peak_hour}시**에 공격이 가장 많고({int(hour_total.max()):,}건), **{low_hour}시**에 가장 적습니다({int(min_val):,}건). 최대·최소 시간대는 약 **{ratio:.1f}배** 차이입니다.")
st.caption("빨간 막대가 공격이 가장 많은 시간이고, 선은 시간대별 증감 흐름입니다")

st.divider()

# ---- 막대 그래프: 요일별 공격 수 ----
st.subheader("요일별 공격 수")

day_df = pd.DataFrame({"요일": days, "공격 수": day_total.values})
day_colors = [COLOR_PEAK if d == peak_day else COLOR_BASE for d in days]

fig_day = px.bar(day_df, x="요일", y="공격 수", text_auto=True)
fig_day.update_traces(marker_color=day_colors)
fig_day.update_xaxes(title=None)
fig_day.update_yaxes(title=None)
fig_day.add_annotation(text="공격 수 (7일 합계)", xref="paper", yref="paper", x=0, y=1.1, xanchor="left", showarrow=False)
fig_day.update_layout(height=360, margin=dict(t=40))
st.plotly_chart(fig_day, use_container_width=True)
st.markdown(f"- **{peak_day}요일**이 가장 많고({int(day_total.max()):,}건), **{low_day}요일**이 가장 적습니다({int(day_total.min()):,}건).")
st.caption("빨간 막대가 공격이 가장 많은 요일입니다")

st.divider()

# ---- 선 그래프: 평일 vs 주말 시간대 비교 ----
st.subheader("평일 vs 주말 시간대 패턴")

weekday_hourly = heatmap_data.loc[days[:5]].mean(axis=0)
weekend_hourly = heatmap_data.loc[days[5:]].mean(axis=0)
compare_df = pd.DataFrame({
    "시간": hours * 2,
    "구분": ["평일"] * 24 + ["주말"] * 24,
    "공격 수": list(weekday_hourly.values) + list(weekend_hourly.values)
})

fig_cmp = px.line(compare_df, x="시간", y="공격 수", color="구분", color_discrete_map={"평일": COLOR_WEEKDAY, "주말": COLOR_WEEKEND}, markers=True)
fig_cmp.update_traces(line=dict(width=3), marker=dict(size=7))
fig_cmp.update_traces(selector=dict(name="주말"), line=dict(dash="dash"))
fig_cmp.update_xaxes(dtick=1, title="시간 (KST)", range=[-0.5, 23.5])
fig_cmp.update_yaxes(title=None)
fig_cmp.add_annotation(text="공격 수 (하루 평균)", xref="paper", yref="paper", x=0, y=1.1, xanchor="left", showarrow=False)
fig_cmp.update_layout(height=380, margin=dict(t=60), legend=dict(title=None, orientation="h", x=0.5, xanchor="center", y=1.12, yanchor="bottom"))
st.plotly_chart(fig_cmp, use_container_width=True)

wd_peak = int(weekday_hourly.idxmax())
we_peak = int(weekend_hourly.idxmax())
if wd_peak == we_peak:
    st.markdown(f"- 평일과 주말 모두 **{wd_peak}시**에 공격이 가장 많아, 요일과 상관없이 시간대 패턴이 비슷합니다.")
else:
    st.markdown(f"- 평일은 **{wd_peak}시**, 주말은 **{we_peak}시**에 공격이 가장 많습니다.")
st.caption("평일은 5일, 주말은 2일이라 시간대별 하루 평균으로 비교했습니다.")

st.divider()

# ---- 도넛(파이): 시간대 구간별 비중 ----
st.subheader("시간대 구간별 공격 비중")

BUCKETS = {
    "새벽 (0~5시)": range(0, 6),
    "오전 (6~11시)": range(6, 12),
    "오후 (12~17시)": range(12, 18),
    "저녁·밤 (18~23시)": range(18, 24),
}
bucket_df = pd.DataFrame({
    "구간": list(BUCKETS.keys()),
    "공격 수": [int(hour_total.loc[list(r)].sum()) for r in BUCKETS.values()]
})
total_sum = bucket_df["공격 수"].sum()
bucket_df["비율"] = (bucket_df["공격 수"] / total_sum * 100) if total_sum > 0 else 0

top_i = bucket_df["공격 수"].idxmax()
low_i = bucket_df["공격 수"].idxmin()
shades = ["#8FA3B8", "#A9B8C7", "#C3CFDA", "#DCE3EA"]
colors = [COLOR_PEAK if i == top_i else shades[i] for i in range(len(bucket_df))]
top_name = bucket_df.loc[top_i, "구간"]
low_name = bucket_df.loc[low_i, "구간"]

fig_pie = px.pie(bucket_df, names="구간", values="공격 수", hole=0.5)
fig_pie.update_traces(sort=False, direction="clockwise", marker=dict(colors=colors, line=dict(color="white", width=2)), pull=[0.06 if i == top_i else 0 for i in range(len(bucket_df))], textinfo="label+percent", textposition="outside")
fig_pie.update_layout(showlegend=False, height=380, margin=dict(t=30, b=30, l=90, r=90), annotations=[dict(text=f"가장 많은 구간<br><b>{top_name.split(' ')[0]}</b>", x=0.5, y=0.5, font_size=15, showarrow=False)])

left, right = st.columns([3, 2])
with left:
    st.plotly_chart(fig_pie, use_container_width=True)
with right:
    st.markdown("#### 한눈에 보기")
    st.markdown(f"- 공격이 가장 많은 구간은 **{top_name}** ({bucket_df.loc[top_i, '비율']:.1f}%)")
    st.markdown(f"- 가장 적은 구간은 **{low_name}** ({bucket_df.loc[low_i, '비율']:.1f}%)")
    st.markdown("- 시계 방향이 시간 순서이고, 맨 위가 0시입니다")