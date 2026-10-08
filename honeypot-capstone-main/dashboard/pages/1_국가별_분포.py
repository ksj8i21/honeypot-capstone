import streamlit as st
import pandas as pd
import plotly.express as px

st.title("🌍 국가별 분포")
st.caption("최근 24시간 기준 · mock data")

country_data = pd.DataFrame({
    "국가": ["러시아", "중국", "미국", "베트남", "브라질", "인도", "독일", "우크라이나"],
    "iso_alpha": ["RUS", "CHN", "USA", "VNM", "BRA", "IND", "DEU", "UKR"],
    "공격 수": [924, 781, 612, 398, 301, 264, 187, 142]
})

fig_map = px.choropleth(
    country_data,
    locations="iso_alpha",
    color="공격 수",
    hover_name="국가",
    color_continuous_scale="Reds",
    projection="natural earth"
)
fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig_map, use_container_width=True)

st.subheader("국가별 공격 Top 8")
st.bar_chart(country_data.set_index("국가")["공격 수"])