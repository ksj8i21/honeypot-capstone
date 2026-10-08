import streamlit as st
import pandas as pd

st.title("🔑 계정 · 비밀번호 Top 10")
st.caption("최근 24시간 기준 · mock data")

ssh_creds = pd.DataFrame({
    "계정": ["root", "admin", "ubuntu", "test", "oracle"],
    "시도 횟수": [612, 388, 301, 190, 142]
})

telnet_creds = pd.DataFrame({
    "계정": ["admin", "root", "user", "guest", "support"],
    "시도 횟수": [455, 340, 210, 178, 96]
})

col1, col2 = st.columns(2)

with col1:
    st.subheader("SSH 계정 Top 5")
    st.bar_chart(ssh_creds.set_index("계정")["시도 횟수"])

with col2:
    st.subheader("Telnet 계정 Top 5")
    st.bar_chart(telnet_creds.set_index("계정")["시도 횟수"])