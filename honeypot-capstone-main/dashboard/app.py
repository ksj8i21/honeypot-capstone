import streamlit as st
import pandas as pd

st.set_page_config(page_title="허니팟 대시보드", layout="wide")

st.title("🛡️ 공격 개요")
st.caption("최근 24시간 기준 · mock data")

total_attacks = 3842
active_sessions = 7
unique_ips = 614
top_country = "러시아 (24%)"

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 공격 시도 (24h)", f"{total_attacks:,}", "+12.4%")
col2.metric("활성 세션", active_sessions)
col3.metric("고유 공격 IP", f"{unique_ips:,}", "-3.1%")
col4.metric("최다 공격 국가", top_country)

st.divider()
st.subheader("시간대별 공격 추이")

hourly_data = pd.DataFrame({
    "시간": list(range(24)),
    "공격 수": [12,8,6,4,3,3,5,9,14,18,22,27,31,29,26,24,28,34,41,38,33,25,19,15]
})
st.line_chart(hourly_data, x="시간", y="공격 수")

st.subheader("프로토콜별 공격 비중")

protocol_data = pd.DataFrame({
    "프로토콜": ["SSH", "Telnet"],
    "공격 수": [2310, 1532]
})
st.bar_chart(protocol_data, x="프로토콜", y="공격 수")