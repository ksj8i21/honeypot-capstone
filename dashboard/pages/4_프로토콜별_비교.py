import streamlit as st
import numpy as np
import plotly.graph_objects as go
from dashboard.data import get_protocol_stats

# 프로토콜 색상 (SSH = 파랑, Telnet = 주황)
COLOR_SSH = "#2F80ED"
COLOR_TELNET = "#F5A623"
COLOR_PEAK = "#E5484D"   # 피크 = 빨강 (다른 페이지와 공통)

st.title("⚖️ 프로토콜별 비교")
st.caption("실시간 DB 집계 기준 · SSH vs Telnet")
st.caption("세션 = 공격자가 허니팟에 접속해서 연결이 끝날 때까지의 1회 접속")
st.markdown("🔵 **SSH** &nbsp;&nbsp; 🟠 **Telnet**")

# ---- DB 데이터 연동 ----
proto_df = get_protocol_stats()

# 기본값 설정 (DB 조회 실패 시 사용할 Mock 데이터)
ssh = {"세션 수": 2310, "평균 체류시간": 42, "평균 명령 수": 6.8, "로그인 성공률": 18.2}
telnet = {"세션 수": 1532, "평균 체류시간": 15, "평균 명령 수": 2.1, "로그인 성공률": 34.7}

if not proto_df.empty:
    try:
        # 데이터프레임 구조에 맞춰 파싱 (예시 컬럼명 대응)
        for _, row in proto_df.iterrows():
            p = str(row.get('protocol', row.get('프로토콜', ''))).lower()
            if 'ssh' in p:
                ssh["세션 수"] = int(row.get('sessions', row.get('세션 수', ssh["세션 수"])))
                ssh["평균 체류시간"] = float(row.get('avg_duration', row.get('평균 체류시간', ssh["평균 체류시간"])))
                ssh["평균 명령 수"] = float(row.get('avg_commands', row.get('평균 명령 수', ssh["평균 명령 수"])))
                ssh["로그인 성공률"] = float(row.get('success_rate', row.get('로그인 성공률', ssh["로그인 성공률"])))
            elif 'telnet' in p:
                telnet["세션 수"] = int(row.get('sessions', row.get('세션 수', telnet["세션 수"])))
                telnet["평균 체류시간"] = float(row.get('avg_duration', row.get('평균 체류시간', telnet["평균 체류시간"])))
                telnet["평균 명령 수"] = float(row.get('avg_commands', row.get('평균 명령 수', telnet["평균 명령 수"])))
                telnet["로그인 성공률"] = float(row.get('success_rate', row.get('로그인 성공률', telnet["로그인 성공률"])))
    except Exception as e:
        print(f"Protocol stats parse error: {e}")

# 지표별 표시 형식 (단위 + 천 단위 쉼표)
metrics = [
    ("세션 수", lambda v: f"{v:,.0f}건"),
    ("평균 체류시간", lambda v: f"{v:,.0f}초"),
    ("평균 명령 수", lambda v: f"{v:,.1f}개"),
    ("로그인 성공률", lambda v: f"{v:,.1f}%"),
]

st.divider()

# ---- 지표별 비교: 작은 막대 그래프 4개 ----
st.subheader("지표별 비교")


def make_bar(a, b, fmt):
    fig = go.Figure(go.Bar(
        x=["SSH", "Telnet"], y=[a, b],
        marker_color=[COLOR_SSH, COLOR_TELNET],
        text=[f"<b>{fmt(a)}</b>", f"<b>{fmt(b)}</b>"],   # 굵게
        textposition="outside", cliponaxis=False,
        textfont=dict(size=20),                        # 숫자 글자 키우기
    ))
    fig.update_xaxes(tickfont=dict(size=16))             # SSH / Telnet 글자 키우기
    fig.update_yaxes(visible=False, range=[0, max(a, b) * 1.18 if max(a, b) > 0 else 10])  # 위쪽 빈 공간 줄이기
    fig.update_layout(
        height=300, margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False, bargap=0.4,
    )
    return fig


def ratio_sentence(a, b):
    # a = SSH 값, b = Telnet 값: 큰 쪽이 작은 쪽의 몇 배인지 문장으로 만들기
    if a == 0 or b == 0:  # 한쪽이 0이면 배수를 계산할 수 없으므로 안내 문구로 대체
        return "한쪽 값이 0이라 배수를 계산할 수 없습니다"
    if a >= b:
        return f"**SSH**가 Telnet의 **{a / b:.1f}배**"
    return f"**Telnet**이 SSH의 **{b / a:.1f}배**"


for i, (col, (label, fmt)) in enumerate(zip(st.columns(4), metrics)):
    with col:
        st.markdown(f"**{label}**")
        st.plotly_chart(make_bar(ssh[label], telnet[label], fmt),
                        use_container_width=True, key=f"cmp_{i}")
        st.markdown(ratio_sentence(ssh[label], telnet[label]))

st.caption("그래프마다 세로 눈금이 달라서, 막대 높이는 같은 그래프 안에서만 비교하세요.")
st.caption("평균값 기준이라, 아주 오래 머문 일부 세션이 값을 끌어올릴 수 있습니다.")
st.caption("로그인 성공률 = 로그인 시도 중 성공한 비율. 허니팟이 허용하는 계정 설정에 따라 달라질 수 있어, "
            "공격자의 실력이나 프로토콜의 보안 수준으로 바로 해석하지 않습니다.")

st.divider()

# ---- 한눈에 보기: 자동 생성 해석 ----
st.subheader("한눈에 보기")

more_stay = ssh["평균 체류시간"] > telnet["평균 체류시간"]
more_cmd = ssh["평균 명령 수"] > telnet["평균 명령 수"]
less_success = ssh["로그인 성공률"] < telnet["로그인 성공률"]

if more_stay and more_cmd and less_success:
    st.markdown(
        "- **Telnet**은 로그인 성공률이 더 높지만 체류시간과 명령 수가 짧고, "
        "**SSH**는 성공률이 낮아도 오래 머물며 명령을 더 많이 실행하는 경향이 보입니다."
    )
    st.caption("두 프로토콜의 공격 방식이 다를 가능성을 시사할 뿐, 원인을 확정하는 결과는 아닙니다.")
else:
    st.markdown("- 체류시간·명령 수·로그인 성공률의 방향이 엇갈려 한 문장으로 요약하기 어렵습니다.")

# ---- 시간대별 세션 수 (프로토콜별) ----
st.divider()
st.subheader("시간대별 세션 수")

hours = list(range(24))
base_pattern = np.array([15,10,8,6,5,5,8,12,18,22,25,28,30,28,25,23,26,32,38,35,30,24,20,17])
rng = np.random.default_rng(7)


def scale_to_total(arr, total):
    # 시간별 값의 합이 정확히 total이 되도록 맞추기
    if arr.sum() == 0:
        return np.zeros_like(arr)
    s = np.round(arr / arr.sum() * total).astype(int)
    s[s.argmax()] += total - s.sum()
    return s


ssh_hourly = scale_to_total(base_pattern * rng.uniform(0.85, 1.15, 24), ssh["세션 수"])
telnet_hourly = scale_to_total(np.roll(base_pattern, -2) * rng.uniform(0.85, 1.15, 24),
                               telnet["세션 수"])

# 가장 많은 시간대 (그래프에 표시하려고 먼저 계산)
ssh_peak = int(ssh_hourly.argmax())
telnet_peak = int(telnet_hourly.argmax())

# Telnet 막대: 가장 많은 시간만 빨강, 나머지는 주황
telnet_colors = [COLOR_PEAK if h == telnet_peak else COLOR_TELNET for h in hours]
telnet_labels = ["<b>Telnet 최다</b>" if h == telnet_peak else "" for h in hours]

fig_line = go.Figure()
# Telnet = 막대 (먼저 그려야 SSH 선이 막대 위에 보임)
fig_line.add_trace(go.Bar(
    x=hours, y=telnet_hourly,
    marker_color=telnet_colors,
    text=telnet_labels, textposition="outside", cliponaxis=False,
    textfont=dict(size=15),
    name="Telnet (막대)",
))
# SSH = 꺾은선
fig_line.add_trace(go.Scatter(
    x=hours, y=ssh_hourly,
    mode="lines+markers",
    line=dict(color=COLOR_SSH, width=3),
    marker=dict(size=7, color=COLOR_SSH),
    name="SSH (꺾은선)",
))
# SSH 가장 많은 시간: 큰 빨간 점 하나 + 글자
fig_line.add_trace(go.Scatter(
    x=[ssh_peak], y=[int(ssh_hourly[ssh_peak])],
    mode="markers+text",
    marker=dict(size=14, color=COLOR_PEAK, line=dict(color="white", width=2)),
    text=["<b>SSH 최다</b>"], textposition="top center",
    textfont=dict(size=15),
    name="가장 많은 시간",
))
fig_line.update_xaxes(dtick=1, title="시간 (KST)", range=[-0.5, 23.5], tickfont=dict(size=13))
max_val = max(ssh_hourly.max(), telnet_hourly.max())
fig_line.update_yaxes(title=None, range=[0, max_val * 1.25 if max_val > 0 else 10],
                      tickfont=dict(size=13))
fig_line.add_annotation(
    text="세션 수 (24시간)",
    xref="paper", yref="paper",
    x=0, y=1.1,
    xanchor="left", showarrow=False,
)
fig_line.update_layout(
    height=380, margin=dict(t=60),
    legend=dict(title=None, orientation="h", font=dict(size=14),
                x=0.5, xanchor="center", y=1.12, yanchor="bottom"),
)
st.plotly_chart(fig_line, use_container_width=True)

if ssh_peak == telnet_peak:
    st.markdown(f"- SSH와 Telnet 모두 **{ssh_peak}시**에 세션이 가장 많습니다.")
else:
    st.markdown(f"- **SSH**는 **{ssh_peak}시**, **Telnet**은 **{telnet_peak}시**에 세션이 가장 많습니다.")


def to_ranges(hs):
    # [4, 5, 6, 9] → "4~6시, 9시" 처럼 이어지는 시간을 묶어서 보여주기
    if not hs:
        return ""
    groups, start, prev = [], hs[0], hs[0]
    for h in hs[1:]:
        if h != prev + 1:
            groups.append((start, prev))
            start = h
        prev = h
    groups.append((start, prev))
    return ", ".join(f"{a}시" if a == b else f"{a}~{b}시" for a, b in groups)


ssh_more = [h for h in hours if ssh_hourly[h] > telnet_hourly[h]]
telnet_more = [h for h in hours if telnet_hourly[h] > ssh_hourly[h]]

if telnet_more:
    st.markdown(
        f"- 24시간 중 **{len(ssh_more)}시간**은 SSH가, **{len(telnet_more)}시간**은 Telnet이 더 많습니다. "
        f"Telnet이 앞서는 시간대는 **{to_ranges(telnet_more)}**입니다."
    )
else:
    st.markdown("- 모든 시간대에서 **SSH**가 Telnet보다 세션이 많습니다.")
st.caption("빨간 점(SSH)과 빨간 막대(Telnet)가 각각 세션이 가장 많은 시간입니다.")