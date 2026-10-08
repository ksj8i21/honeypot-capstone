import streamlit as st
import pandas as pd

st.title("🤖 AI 위협분석")
st.caption("AI가 분류한 공격 의도 및 심각도 · mock data")

# ---- mock data (나중에 ai_analysis 테이블 결과로 교체) ----
intent_data = pd.DataFrame({
    "공격 의도": ["봇넷가담", "정찰", "코인채굴", "자격증명탈취", "랜섬웨어", "기타"],
    "건수": [412, 289, 156, 98, 34, 61]
})

severity_data = pd.DataFrame({
    "심각도": [1, 2, 3, 4, 5],
    "건수": [180, 310, 245, 210, 105]
})

sample_cases = pd.DataFrame({
    "cmd_hash": ["a1f9c2...", "7e3b81...", "f02d4e...", "9c7a10..."],
    "프로토콜": ["Telnet", "SSH", "SSH", "Telnet"],
    "의도": ["봇넷가담", "정찰", "코인채굴", "자격증명탈취"],
    "심각도": [4, 2, 5, 3],
    "요약": [
        "Mirai 계열 봇넷 감염 시도, busybox 다운로드 및 실행",
        "시스템 정보 수집 목적의 명령 나열(uname, whoami 등)",
        "XMRig 마이너 설치 스크립트 실행 시도",
        "저장된 SSH 키 및 credential 파일 탐색"
    ]
})

# ---- 공격 의도 분포 ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("공격 의도 분포")
    st.bar_chart(intent_data.set_index("공격 의도")["건수"])

with col2:
    st.subheader("심각도 분포 (1~5)")
    st.bar_chart(severity_data.set_index("심각도")["건수"])

st.divider()

# ---- 대표 사례 테이블 ----
st.subheader("대표 공격 패턴 사례")
st.dataframe(sample_cases, use_container_width=True, hide_index=True)