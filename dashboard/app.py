import streamlit as st
import pandas as pd
import plotly.express as px
from data import get_protocol_stats, get_time_patterns, get_overview, get_country_distribution, COUNTRY_INFO

# 팀 공통 색상 (색의 의미를 한곳에서 관리)
COLOR_SSH = "#4C8DFF"      # SSH = 파랑
COLOR_TELNET = "#F5A623"   # Telnet = 주황
COLOR_NORMAL = "#8FA3B8"   # 평소 = 회색
COLOR_PEAK = "#E5484D"     # 피크 = 빨강

st.set_page_config(page_title="허니팟 대시보드", layout="wide")

st.title("🛡️ 공격 개요")

# 상단 지표 계산 (sessions 테이블 기반 요약)
overview = get_overview().iloc[0]
total_attacks = int(overview["total_sessions"])
unique_ips = int(overview["unique_ips"])
first_day = pd.to_datetime(overview["first_ts"], utc=True).tz_convert("Asia/Seoul").date()
last_day = pd.to_datetime(overview["last_ts"], utc=True).tz_convert("Asia/Seoul").date()
collect_days = round((pd.to_datetime(overview["last_ts"], utc=True) - pd.to_datetime(overview["first_ts"], utc=True)) / pd.Timedelta(days=1))

st.caption(f"DB 집계 기준 · {first_day} ~ {last_day} (KST)")

country_df = get_country_distribution()
known_df = country_df[country_df["country_code"].notna()].sort_values("attempts", ascending=False)
if known_df.empty:
    top_country = "-"
else:
    top = known_df.iloc[0]
    top_name = COUNTRY_INFO.get(top["country_code"], {}).get("kr", top["country"])
    top_share = top["attempts"] / known_df["attempts"].sum() * 100
    top_country = f"{top_name} ({top_share:.0f}%)"

proto_df = get_protocol_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 공격 시도", f"{total_attacks:,}")
col2.metric("수집 기간", f"{collect_days}일", help=f"{first_day} ~ {last_day} (KST)")
col3.metric("고유 공격 IP", f"{unique_ips:,}")
col4.metric("최다 공격 국가", top_country, help="국가가 확인된 세션 중 비율입니다.")

st.divider()


def style_chart(fig, y_title):
    """y축 제목을 가로 글씨로 축 위쪽에 표시하고 범례는 숨김"""
    fig.update_layout(
        yaxis_title=None,
        showlegend=False,
        margin=dict(t=40),
        annotations=[dict(
            text=y_title, xref="paper", yref="paper",
            x=0, y=1, xanchor="left", yanchor="bottom",
            showarrow=False,
        )],
    )
    return fig


# ---- 시간대별: 피크 시간만 빨강 (DB 데이터 연동) ----
st.subheader("시간대별 공격 추이")

time_df = get_time_patterns()
# 시간대별로 그룹화하여 합산
hourly_data = time_df.groupby('hour_of_day', as_index=False)['attempts'].sum()
hourly_data.rename(columns={'hour_of_day': '시간', 'attempts': '공격 수'}, inplace=True)

# 0~23시 누락된 시간이 있다면 채워주기
full_hours = pd.DataFrame({"시간": list(range(24))})
hourly_data = pd.merge(full_hours, hourly_data, on="시간", how="left").fillna(0)

peak_value = hourly_data["공격 수"].max()
hourly_data["구분"] = hourly_data["공격 수"].apply(
    lambda v: "피크" if v == peak_value and v > 0 else "일반"
)

fig_hour = px.bar(
    hourly_data, x="시간", y="공격 수", color="구분",
    color_discrete_map={"일반": COLOR_NORMAL, "피크": COLOR_PEAK},
)
fig_hour.update_xaxes(dtick=1)
style_chart(fig_hour, "공격 수")
st.plotly_chart(fig_hour, use_container_width=True)

if not hourly_data.empty and peak_value > 0:
    peak_hour = hourly_data.loc[hourly_data["공격 수"].idxmax(), "시간"]
    st.caption(f"🔴 피크 시간: {int(peak_hour)}시 ({int(peak_value)}건)")
else:
    st.caption("🔴 피크 시간: 데이터 없음")


# ---- 프로토콜별: SSH 파랑 / Telnet 주황 (DB 데이터 연동) ----
st.subheader("프로토콜별 공격 비중")

protocol_data = proto_df[['protocol', 'sessions']].copy()
protocol_data.columns = ["프로토콜", "공격 수"]
# 프로토콜 이름을 대문자 혹은 맞춤형으로 변환 (ssh -> SSH 등)
protocol_data["프로토콜"] = protocol_data["프로토콜"].str.upper()

fig_proto = px.bar(
    protocol_data, x="프로토콜", y="공격 수", color="프로토콜",
    color_discrete_map={"SSH": COLOR_SSH, "TELNET": COLOR_TELNET, "TELNET": COLOR_TELNET},
    text_auto=True,
)
style_chart(fig_proto, "공격 수")
st.plotly_chart(fig_proto, use_container_width=True)