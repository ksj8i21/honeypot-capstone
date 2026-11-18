import streamlit as st
import pandas as pd
import plotly.express as px
from data import get_ai_threat_summary, get_ai_patterns

# 팀 공통 색상 (다른 페이지와 동일)
COLOR_SSH = "#4C8DFF"      # SSH = 파랑
COLOR_TELNET = "#F5A623"   # Telnet = 주황
COLOR_NORMAL = "#8FA3B8"   # 일반 = 회색
COLOR_PEAK = "#E5484D"     # 최다 = 빨강

# 심각도 색상: 연한 빨강 → 진한 빨강 (SSH 파랑, Telnet 주황과 겹치지 않게)
SEVERITY_LABELS = {1: "1 낮음", 2: "2 주의", 3: "3 보통", 4: "4 높음", 5: "5 치명적"}
SEVERITY_COLORS = {
    "1 낮음": "#FCD9D2", "2 주의": "#F9A99A", "3 보통": "#F07A68",
    "4 높음": "#D93A3A", "5 치명적": "#8E1B1B",
}

st.title("🤖 AI 위협분석")
st.caption("DB 집계 기준 (수집 전체 기간) · AI가 분류한 공격 의도와 심각도")

# ---- DB 데이터 연동 ----
raw_ai_df = get_ai_threat_summary()

analyzed = raw_ai_df[raw_ai_df["intent"].notna()]
pending_count = int(raw_ai_df.loc[raw_ai_df["intent"].isna(), "cnt"].sum())

intent_by_proto = (
    analyzed.assign(프로토콜=analyzed["protocol"].map({"ssh": "SSH", "telnet": "Telnet"}))
    .groupby(["intent", "프로토콜"], as_index=False)["cnt"].sum()
    .rename(columns={"intent": "의도", "cnt": "건수"})
)
severity_data = (
    analyzed.dropna(subset=["severity"])
    .groupby("severity")["cnt"].sum()
    .reindex(range(1, 6), fill_value=0)
    .rename_axis("심각도").reset_index(name="건수")
)

patterns = get_ai_patterns()
cases = (
    patterns[patterns["intent"].notna()]
    .sort_values(["severity", "sessions"], ascending=False, kind="stable")
    .head(6)
)
cases = pd.DataFrame({
    "패턴 ID": cases["cmd_hash"].str[:6] + "…",
    "프로토콜": cases["protocols"].map(
        lambda ps: ", ".join({"ssh": "🔵 SSH", "telnet": "🟠 Telnet"}.get(p, p) for p in sorted(ps))
    ),
    "의도": cases["intent"],
    "심각도": cases["severity"],
    "세션 수": cases["sessions"],
    "요약": cases["summary"],
})

severity_data["등급"] = severity_data["심각도"].map(SEVERITY_LABELS)

# ---- 요약 숫자 계산 ----
intent_total = intent_by_proto.groupby("의도")["건수"].sum().sort_values(ascending=False)
done_count = int(intent_total.sum())
total_sev_count = severity_data["건수"].sum()
avg_severity = (severity_data["심각도"] * severity_data["건수"]).sum() / total_sev_count if total_sev_count > 0 else 0
high_sev_count = severity_data.loc[severity_data["심각도"] >= 4, "건수"].sum()
high_ratio = (high_sev_count / total_sev_count * 100) if total_sev_count > 0 else 0


def y_label_on_top(fig, text):
    """y축 제목을 가로 글씨로 축 위쪽에 표시"""
    fig.update_layout(
        yaxis_title=None,
        annotations=[dict(
            text=text, xref="paper", yref="paper",
            x=0, y=1, xanchor="left", yanchor="bottom", showarrow=False,
        )],
    )
    return fig


# ---- 상단 요약 카드 ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("분석 완료", f"{done_count:,}건")
c2.metric("분석 대기", f"{pending_count:,}건", help="아직 AI가 분석하지 않은 건입니다.")
c3.metric("평균 심각도", f"{avg_severity:.1f} / 5")
c4.metric("고위험(4~5) 비율", f"{high_ratio:.1f}%")
st.caption("분석 대기: 아직 AI가 분석하지 않은 건")
st.caption("건수는 공격 패턴 수가 아니라 명령을 실행한 세션 수입니다.")

st.divider()

# ---- 의도 분포(왼쪽) + 심각도 분포(오른쪽) ----
left, right = st.columns(2)

with left:
    st.subheader("공격 의도 분포")
    intent_df = intent_total.reset_index()
    intent_df["강조"] = ["최다" if i == 0 else "일반" for i in range(len(intent_df))]
    fig_intent = px.bar(
        intent_df, x="건수", y="의도", orientation="h", color="강조",
        color_discrete_map={"최다": COLOR_PEAK, "일반": COLOR_NORMAL},
        text_auto=True,
    )
    fig_intent.update_yaxes(autorange="reversed", title=None)  # 1위를 위쪽에
    max_val = intent_df["건수"].max() if not intent_df.empty else 10
    fig_intent.update_xaxes(range=[0, max_val * 1.15], title="건수")
    fig_intent.update_traces(textposition="outside", cliponaxis=False)
    fig_intent.update_layout(showlegend=False, height=340, margin=dict(t=40))
    st.plotly_chart(fig_intent, use_container_width=True)

with right:
    st.subheader("심각도 분포 (1~5)")
    fig_sev = px.bar(
        severity_data, x="등급", y="건수", color="등급",
        color_discrete_map=SEVERITY_COLORS,
        category_orders={"등급": list(SEVERITY_LABELS.values())},
        text_auto=True,
    )
    fig_sev.update_xaxes(tickangle=0, title=None)
    max_sev_val = severity_data["건수"].max() if not severity_data.empty else 10
    fig_sev.update_yaxes(range=[0, max_sev_val * 1.15])
    fig_sev.update_traces(textposition="outside", cliponaxis=False)
    fig_sev.update_layout(showlegend=False, height=340, margin=dict(t=40))
    y_label_on_top(fig_sev, "건수")
    st.plotly_chart(fig_sev, use_container_width=True)

st.divider()

# ---- SSH vs Telnet: 프로토콜별 의도 비교 ----
st.subheader("프로토콜별 공격 의도 비교")

fig_proto = px.bar(
    intent_by_proto, x="의도", y="건수", color="프로토콜", barmode="group",
    color_discrete_map={"SSH": COLOR_SSH, "Telnet": COLOR_TELNET},
    category_orders={"의도": list(intent_total.index), "프로토콜": ["SSH", "Telnet"]},
    text_auto=True,
)
fig_proto.update_xaxes(tickangle=0, title=None)
max_proto_val = intent_by_proto["건수"].max() if not intent_by_proto.empty else 10
fig_proto.update_yaxes(range=[0, max_proto_val * 1.2])
fig_proto.update_traces(textposition="outside", cliponaxis=False)
fig_proto.update_layout(height=360, margin=dict(t=40), legend_title_text="")
y_label_on_top(fig_proto, "건수")
st.plotly_chart(fig_proto, use_container_width=True)

if not intent_by_proto.empty:
    top_by_proto = (
        intent_by_proto.loc[intent_by_proto.groupby("프로토콜")["건수"].idxmax()]
        .set_index("프로토콜")["의도"]
    )
    st.info(
        ", ".join(f"{proto}에서는 **{intent}**" for proto, intent in top_by_proto.items())
        + " 의도가 가장 많이 분류되었습니다."
    )

st.divider()

# ---- 대표 공격 패턴 사례 (심각도 높은 순) ----
st.subheader("대표 공격 패턴 사례")
st.dataframe(
    cases,
    use_container_width=True,
    hide_index=True,
    column_config={
        "심각도": st.column_config.ProgressColumn(
            "심각도", min_value=0, max_value=5, format="%d / 5"
        ),
        "요약": st.column_config.TextColumn("요약", width="large"),
    },
)
st.caption(
    "※ AI가 자동으로 분류한 결과라 오분류가 있을 수 있습니다. "
    "같은 명령 묶음(cmd_hash)은 대표 1건만 분석해 전체에 적용합니다."
)