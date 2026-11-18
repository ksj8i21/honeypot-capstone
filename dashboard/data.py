import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

@st.cache_data(ttl=300)
def fetch_data(rpc_name, mock_data, params=None):
    if sb:
        try:
            if params:
                res = sb.rpc(rpc_name, params).execute()
            else:
                res = sb.rpc(rpc_name).execute()
            if res.data:
                return pd.DataFrame(res.data)
        except Exception as e:
            print(f"[{rpc_name}] 실패: {e}")
    return pd.DataFrame(mock_data)

def get_country_distribution():
    return fetch_data('get_country_distribution', {"country": ["US", "CN", "KR"], "attempts": [1500, 1200, 150]})

def get_top_auth_attempts():
    return fetch_data('get_top_auth_attempts', {"username": ["root", "admin"], "password": ["1234", "admin"], "attempts": [5000, 3200]})

def get_protocol_stats():
    return fetch_data('get_protocol_stats', {"protocol": ["ssh", "telnet"], "sessions": [12000, 8500], "avg_duration": [45.5, 12.3]})

def get_time_patterns():
    return fetch_data('get_time_patterns', {"day_of_week": ["Monday"], "hour_of_day": [14], "attempts": [500]})

def get_ai_threat_summary():
    return fetch_data('get_ai_threat_summary', {"intent": ["자격증명탈취"], "severity": [4], "cnt": [450]})

@st.cache_data(ttl=300)
def fetch_auth_rankings(protocol, target_type):
    """
    protocol: 'ssh' 또는 'telnet'
    target_type: 'username' 또는 'password'
    """
    rpc_name = 'get_auth_usernames' if target_type == 'username' else 'get_auth_passwords'
    
    if sb:
        try:
            res = sb.rpc(rpc_name, {"p_protocol": protocol}).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                if not df.empty:
                    return df
        except Exception as e:
            print(f"DB Fetch Error (Auth Rankings {protocol} {target_type}): {e}")
            
    # DB 연결 전이거나 실패 시 기존 Mock 데이터 반환
    if target_type == 'username':
        if protocol == 'ssh':
            return pd.DataFrame({"항목": ["root", "admin", "ubuntu", "test", "oracle", "user", "postgres", "pi", "git", "guest"], "시도_횟수": [612, 388, 301, 190, 142, 120, 98, 85, 72, 60]})
        else:
            return pd.DataFrame({"항목": ["admin", "root", "user", "guest", "support", "default", "supervisor", "ubnt", "pi", "operator"], "시도_횟수": [455, 340, 210, 178, 96, 88, 75, 64, 51, 40]})
    else:
        if protocol == 'ssh':
            return pd.DataFrame({"항목": ["123456", "admin", "password", "root", "12345678", "qwerty", "1234", "test", "ubuntu", "toor"], "시도_횟수": [540, 410, 320, 280, 210, 175, 150, 120, 95, 70]})
        else:
            return pd.DataFrame({"항목": ["admin", "1234", "12345", "password", "default", "123456", "support", "root", "pass", "user"], "시도_횟수": [480, 390, 310, 240, 200, 170, 130, 105, 80, 55]})