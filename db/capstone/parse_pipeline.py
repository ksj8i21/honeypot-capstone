import json
from supabase import create_client

# Supabase 정보
SUPABASE_URL = "https://bdgjxqagttkkpswhwnzv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJkZ2p4cWFndHRra3Bzd2h3bnp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1ODYxOTEsImV4cCI6MjEwNTE2MjE5MX0.f2MrYnsr_rcn6AWHNJjz6heAvFnWOMLOdL-yDZdoP7M"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1단계에서 만든 sample_cowrie.json 파일 읽기
with open('sample_cowrie.json', 'r', encoding='utf-8') as f:
    count = 0
    for line in f:
        log = json.loads(line.strip())
        
        # 필요한 항목만 쏙쏙 뽑아내기
        data = {
            "session_id": log.get("session"),
            "timestamp": log.get("timestamp"),
            "src_ip": log.get("src_ip"),
            "event_id": log.get("eventid"),
            "username": log.get("username"),
            "password": log.get("password"),
            "input_command": log.get("input")
        }
        
        # DB에 하나씩 집어넣기
        supabase.table("honeypot_logs").insert(data).execute()
        count += 1

print(f"[SUCCESS] 총 {count}개의 해커 공격 로그를 DB에 일괄 저장했습니다!")