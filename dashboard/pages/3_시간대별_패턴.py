import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.title("⏰ 시간대별 패턴")
st.caption("최근 7일 기준 · mock data")

days = ["월", "화", "수", "목", "금", "토", "일"]
hours = list(range(24))

np.random.seed(42)
base_pattern = np.array([15,10,8,6,5,5,8,12,18,22,25,28,30,28,25,23,26,32,38,35,30,24,20,17])
heatmap_data = pd.DataFrame(
    [base_pattern * np.random.uniform(0.7, 1.3) for _ in days],
    index=days,
    columns=hours
).round(0)

st.subheader("요일 × 시간대 공격 히트맵")

fig_heat = px.imshow(
    heatmap_data,
    labels=dict(x="시간", y="요일", color="공격 수"),
    color_continuous_scale="Reds",
    aspect="auto"
)
st.plotly_chart(fig_heat, use_container_width=True)
st.caption("색이 진할수록 해당 요일·시간대에 공격이 집중됨")