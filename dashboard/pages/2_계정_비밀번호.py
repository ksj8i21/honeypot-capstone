import html
import streamlit as st
import pandas as pd
import plotly.express as px
from data import fetch_auth_rankings, show_chart

# 팀 공통 색상 (1페이지와 동일)
COLOR_SSH = "#4C8DFF"      # SSH = 파랑
COLOR_TELNET = "#F5A623"   # Telnet = 주황
COLOR_COMMON = "#8FA3B8"   # 공통 = 회색

st.title("🔑 계정 · 비밀번호 Top 10")
st.caption("DB 집계 기준 (수집 전체 기간)")
st.caption("봇이 로그인 창에 보낸 제어 문자 섞인 입력(`enable\\x00` 등)은 집계에서 제외했습니다.")

# ---- DB 데이터 연동 ----
ssh_users = fetch_auth_rankings('ssh', 'username')
telnet_users = fetch_auth_rankings('telnet', 'username')
ssh_pw = fetch_auth_rankings('ssh', 'password')
telnet_pw = fetch_auth_rankings('telnet', 'password')


def mask(pw):
    """비밀번호 마스킹: 앞 2글자만 보이고 나머지는 *"""
    if pw == "":
        return "(빈 값)"
    if len(pw) <= 2:
        return "*" * len(pw)
    return pw[:2] + "*" * (len(pw) - 2)


def rank_chart(df, color, max_value):
    """순위 번호가 붙은 가로 막대 그래프 (1위가 맨 위)"""
    data = df.copy()
    data["표시"] = [f"{i}. {name}" for i, name in enumerate(data["항목"], start=1)]
    fig = px.bar(
        data, x="시도_횟수", y="표시", orientation="h",
        text_auto=True, color_discrete_sequence=[color],
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(range=[0, max_value * 1.15 if max_value > 0 else 10], title="시도 횟수")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(margin=dict(t=10), showlegend=False, height=420)
    return fig


def show_pair(ssh_df, telnet_df):
    """SSH(왼쪽)와 Telnet(오른쪽)을 같은 눈금으로 나란히 표시"""
    max_val_ssh = ssh_df["시도_횟수"].max() if not ssh_df.empty else 0
    max_val_tel = telnet_df["시도_횟수"].max() if not telnet_df.empty else 0
    max_value = max(max_val_ssh, max_val_tel)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔵 SSH")
        show_chart(rank_chart(ssh_df, COLOR_SSH, max_value), use_container_width=True)
    with col2:
        st.subheader("🟠 Telnet")
        show_chart(rank_chart(telnet_df, COLOR_TELNET, max_value), use_container_width=True)


def chips(names, color):
    """계정 이름을 색깔 칩(작은 라벨)으로 표시"""
    if not names:
        return "<span style='opacity:.6'>없음</span>"
    return "".join(
        f"<span style='display:inline-block;margin:3px 6px 3px 0;padding:3px 10px;"
        f"border-radius:14px;background:{color}33;border:1px solid {color};"
        f"font-size:14px;'>{html.escape(n)}</span>"
        for n in names
    )


# ---- 비밀번호 유형 분류 ----
KEYBOARD = {"qwerty", "qwerty123", "asdf", "1q2w3e", "qazwsx", "zxcvbn"}
KNOWN_ACCOUNTS = set(ssh_users["항목"]) | set(telnet_users["항목"])
PW_TYPES = ["숫자만", "흔한 계정명과 동일", "키보드 배열", "영문 단어", "빈 값", "기타"]


def classify(pw):
    low = str(pw).lower()
    if low == "":
        return "빈 값"
    if low.isdigit():
        return "숫자만"
    if low in KNOWN_ACCOUNTS:
        return "흔한 계정명과 동일"
    if low in KEYBOARD:
        return "키보드 배열"
    if low.isalpha():
        return "영문 단어"
    return "기타"


def type_share(df, protocol):
    """유형별 시도 횟수를 합쳐서 비율(%)로 바꿈"""
    if df.empty:
        return pd.DataFrame(columns=["유형", "비율(%)", "프로토콜"])
    temp = df.copy()
    temp["유형"] = temp["항목"].map(classify)
    t = temp.groupby("유형")["시도_횟수"].sum()
    t = t.reindex(PW_TYPES, fill_value=0)
    total = t.sum()
    ratios = (t.values / total * 100).round(1) if total > 0 else [0]*len(PW_TYPES)
    return pd.DataFrame({
        "유형": t.index,
        "비율(%)": ratios,
        "프로토콜": protocol,
    })


tab_user, tab_pw = st.tabs(["계정 Top 10", "비밀번호 Top 10"])

# ================= 계정 탭 =================
with tab_user:
    show_pair(ssh_users, telnet_users)

    st.divider()
    st.subheader("프로토콜별 특징 계정")

    ssh_set = set(ssh_users["항목"])
    telnet_set = set(telnet_users["항목"])
    ssh_only = [a for a in ssh_users["항목"] if a not in telnet_set]
    common = [a for a in ssh_users["항목"] if a in telnet_set]
    telnet_only = [a for a in telnet_users["항목"] if a not in ssh_set]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**🔵 SSH에만 ({len(ssh_only)}개)**")
        st.markdown(chips(ssh_only, COLOR_SSH), unsafe_allow_html=True)
    with c2:
        st.markdown(f"**⚪ 둘 다 ({len(common)}개)**")
        st.markdown(chips(common, COLOR_COMMON), unsafe_allow_html=True)
    with c3:
        st.markdown(f"**🟠 Telnet에만 ({len(telnet_only)}개)**")
        st.markdown(chips(telnet_only, COLOR_TELNET), unsafe_allow_html=True)
    st.caption("각 프로토콜 상위 10위 안에 든 계정 기준 · 순위가 높은 순서")

# ================= 비밀번호 탭 =================
with tab_pw:
    st.subheader("비밀번호 유형 비교")
    st.caption("상위 10개 비밀번호의 시도 횟수 기준 · 원문은 표시하지 않음")

    share = pd.concat(
        [type_share(ssh_pw, "SSH"), type_share(telnet_pw, "Telnet")],
        ignore_index=True,
    )
    # 두 프로토콜 모두 0%인 유형은 숨김
    share = share[share.groupby("유형")["비율(%)"].transform("sum") > 0]

    if not share.empty:
        fig_type = px.bar(
            share, x="유형", y="비율(%)", color="프로토콜", barmode="group",
            color_discrete_map={"SSH": COLOR_SSH, "Telnet": COLOR_TELNET},
            category_orders={"유형": PW_TYPES, "프로토콜": ["SSH", "Telnet"]},
            text_auto=".1f",
        )
        fig_type.update_xaxes(tickangle=0, title=None)
        fig_type.update_yaxes(range=[0, share["비율(%)"].max() * 1.2 if share["비율(%)"].max() > 0 else 10], title=None)
        fig_type.update_traces(textposition="outside", cliponaxis=False)
        fig_type.update_layout(
            margin=dict(t=40), height=380, legend_title_text="",
            annotations=[dict(
                text="비율(%)", xref="paper", yref="paper",
                x=0, y=1, xanchor="left", yanchor="bottom", showarrow=False,
            )],
        )
        show_chart(fig_type, use_container_width=True)

    st.divider()
    st.subheader("비밀번호 Top 10 (마스킹)")
    show_pair(
        ssh_pw.assign(항목=ssh_pw["항목"].map(mask)),
        telnet_pw.assign(항목=telnet_pw["항목"].map(mask)),
    )
    st.caption("🔒 보안을 위해 비밀번호는 앞 2글자만 표시하고 나머지는 *로 가렸습니다.")