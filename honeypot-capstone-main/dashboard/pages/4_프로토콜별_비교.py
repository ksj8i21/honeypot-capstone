import streamlit as st
import pandas as pd

st.title("⚖️ 프로토콜별 비교")
st.caption("SSH vs Telnet · 최근 24시간 기준 · mock data")

# ---- mock data (나중에 실제 집계 쿼리 결과로 교체) ----
ssh_stats = {
    "세션 수": 2310,
    "평균 체류시간(초)": 42,
    "평균 명령 수": 6.8,
    "로그인 성공률": "18.2%",
}
telnet_stats = {
    "세션 수": 1532,
    "평균 체류시간(초)": 15,
    "평균 명령 수": 2.1,
    "로그인 성공률": "34.7%",
}

# ---- 좌우 비교 카드 ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔵 SSH")
    for label, value in ssh_stats.items():
        st.metric(label, value)

with col2:
    st.subheader("🟠 Telnet")
    for label, value in telnet_stats.items():
        st.metric(label, value)

st.divider()

# ---- 표로도 한 번에 비교 ----
st.subheader("한눈에 비교")

compare_df = pd.DataFrame({
    "지표": list(ssh_stats.keys()),
    "SSH": list(ssh_stats.values()),
    "Telnet": list(telnet_stats.values()),
})
st.dataframe(compare_df, use_container_width=True, hide_index=True)