import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# geo.country_code(ISO 2글자) → 지도용 ISO 3글자, 한글 이름. 여기 없는 나라는 영문 이름으로 표시하고 지도에서는 뺀다
COUNTRY_INFO = {
    "US": {"alpha": "USA", "kr": "미국"}, "FR": {"alpha": "FRA", "kr": "프랑스"},
    "IN": {"alpha": "IND", "kr": "인도"}, "CN": {"alpha": "CHN", "kr": "중국"},
    "KR": {"alpha": "KOR", "kr": "대한민국"}, "IR": {"alpha": "IRN", "kr": "이란"},
    "BR": {"alpha": "BRA", "kr": "브라질"}, "SE": {"alpha": "SWE", "kr": "스웨덴"},
    "DE": {"alpha": "DEU", "kr": "독일"}, "RU": {"alpha": "RUS", "kr": "러시아"},
    "UA": {"alpha": "UKR", "kr": "우크라이나"}, "HK": {"alpha": "HKG", "kr": "홍콩"},
    "AR": {"alpha": "ARG", "kr": "아르헨티나"}, "CA": {"alpha": "CAN", "kr": "캐나다"},
    "NL": {"alpha": "NLD", "kr": "네덜란드"}, "PH": {"alpha": "PHL", "kr": "필리핀"},
    "JP": {"alpha": "JPN", "kr": "일본"}, "SG": {"alpha": "SGP", "kr": "싱가포르"},
    "TW": {"alpha": "TWN", "kr": "대만"}, "ID": {"alpha": "IDN", "kr": "인도네시아"},
    "TH": {"alpha": "THA", "kr": "태국"}, "ES": {"alpha": "ESP", "kr": "스페인"},
    "BE": {"alpha": "BEL", "kr": "벨기에"}, "GB": {"alpha": "GBR", "kr": "영국"},
    "VN": {"alpha": "VNM", "kr": "베트남"},
}


@st.cache_data(ttl=300)
def _rpc(rpc_name, params=None):
    if params:
        res = sb.rpc(rpc_name, params).execute()
    else:
        res = sb.rpc(rpc_name).execute()
    return pd.DataFrame(res.data)


def fetch_data(rpc_name, mock_data, params=None):
    # 예외를 _rpc 안에서 잡으면 실패해서 돌려준 mock 이 5분 동안 캐시된다
    if sb:
        try:
            df = _rpc(rpc_name, params)
            if not df.empty:
                return df
        except Exception as e:
            print(f"[{rpc_name}] 실패: {e}")
    st.warning(f"DB에서 값을 가져오지 못해 예시 데이터를 표시합니다. ({rpc_name})")
    return pd.DataFrame(mock_data)


def is_mobile():
    return "Mobi" in st.context.headers.get("User-Agent", "")


def page_title(text):
    # 휴대폰 폭에서 제목이 '프로토콜별 비 / 교' 처럼 낱말 중간에서 끊겼다. 낱말 단위로만 줄바꿈하고 글자를 줄인다
    st.html("<style>h1,h2,h3,p,li{word-break:keep-all!important}@media (max-width:640px){h1{font-size:1.9rem!important}}</style>")
    st.title(text)


def show_chart(fig, movable=False, **kwargs):
    # 휴대폰에서 그래프에 손이 닿으면 확대·이동돼서 화면 스크롤이 막혔다. 지도만 movable 로 움직이게 둔다
    config = {"displayModeBar": False, "scrollZoom": movable, "doubleClick": "reset" if movable else False}
    if not movable:
        fig.update_layout(dragmode=False)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        # 확대를 꺼도 그래프 위에서는 스크롤이 안 되고 아래로 끌면 브라우저 새로고침이 떴다 (S21+ 삼성 인터넷). 폰에서는 그림으로만 그린다
        config["staticPlot"] = is_mobile()
    st.plotly_chart(fig, config=config, **kwargs)


def get_overview():
    return fetch_data('get_overview', {
        "total_sessions": [20500], "unique_ips": [614],
        "first_ts": ["2026-10-04T13:53:05+00:00"], "last_ts": ["2026-10-11T13:53:05+00:00"],
    })

def get_country_distribution():
    return fetch_data('get_country_distribution', {
        "country_code": ["US", "CN", "KR"], "country": ["United States", "China", "South Korea"],
        "attempts": [1500, 1200, 150],
    })

def get_top_auth_attempts():
    return fetch_data('get_top_auth_attempts', {"username": ["root", "admin"], "password": ["1234", "admin"], "attempts": [5000, 3200]})

def get_protocol_stats():
    return fetch_data('get_protocol_stats', {
        "protocol": ["ssh", "telnet"], "sessions": [12000, 8500], "avg_duration": [45.5, 12.3],
        "avg_commands": [6.8, 2.1], "success_rate": [18.2, 34.7],
    })

def get_time_patterns():
    return fetch_data('get_time_patterns', {"day_of_week": ["Monday"], "hour_of_day": [14], "attempts": [500]})

def get_hourly_by_protocol():
    return fetch_data('get_hourly_by_protocol', {
        "protocol": ["ssh", "ssh", "telnet", "telnet"], "hour_of_day": [3, 14, 9, 21], "sessions": [700, 500, 400, 350],
    })

def get_ai_threat_summary():
    return fetch_data('get_ai_threat_summary', {
        "intent": ["자격증명탈취", "봇넷가담", None], "severity": [4, 3, None],
        "protocol": ["ssh", "telnet", "telnet"], "cnt": [450, 900, 30],
    })

def get_ai_patterns(max_rows=200):
    return fetch_data('ai_pattern_stats', {
        "cmd_hash": ["a1f9c2d07b3e"], "intent": ["봇넷가담"], "severity": [4],
        "summary": ["Mirai 계열 봇넷 감염 시도, busybox 다운로드 및 실행"],
        "sessions": [120], "protocols": [["telnet"]],
    }, {"max_rows": max_rows})


MOCK_AUTH = {
    ("ssh", "username"): {"item": ["root", "admin", "ubuntu", "test", "oracle", "user", "postgres", "pi", "git", "guest"], "attempts": [612, 388, 301, 190, 142, 120, 98, 85, 72, 60]},
    ("telnet", "username"): {"item": ["admin", "root", "user", "guest", "support", "default", "supervisor", "ubnt", "pi", "operator"], "attempts": [455, 340, 210, 178, 96, 88, 75, 64, 51, 40]},
    ("ssh", "password"): {"item": ["123456", "admin", "password", "root", "12345678", "qwerty", "1234", "test", "ubuntu", "toor"], "attempts": [540, 410, 320, 280, 210, 175, 150, 120, 95, 70]},
    ("telnet", "password"): {"item": ["admin", "1234", "12345", "password", "default", "123456", "support", "root", "pass", "user"], "attempts": [480, 390, 310, 240, 200, 170, 130, 105, 80, 55]},
}

def fetch_auth_rankings(protocol, target_type):
    """
    protocol: 'ssh' 또는 'telnet'
    target_type: 'username' 또는 'password'
    """
    rpc_name = 'get_auth_usernames' if target_type == 'username' else 'get_auth_passwords'
    df = fetch_data(rpc_name, MOCK_AUTH[(protocol, target_type)], {"p_protocol": protocol})
    return df.rename(columns={"item": "항목", "attempts": "시도_횟수"})
