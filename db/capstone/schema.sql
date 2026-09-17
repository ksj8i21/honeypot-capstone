-- ================================================
-- 허니팟 보안 위협 탐지 시스템 DB 스키마 (schema.sql)
-- Supabase / PostgreSQL 기반 테이블 구조
-- ================================================

CREATE TABLE honeypot_logs (
    id BIGSERIAL PRIMARY KEY,               -- 고유 번호 (PK)
    session_id VARCHAR(100),                -- 해커 접속 세션 ID
    timestamp TIMESTAMP WITH TIME ZONE,     -- 공격 발생 시각
    src_ip VARCHAR(50),                     -- 공격자 IP 주소
    event_id VARCHAR(100),                  -- 이벤트 유형 (로그인 성공, 명령어 입력 등)
    username VARCHAR(100),                  -- 공격자가 시도한 아이디
    password VARCHAR(100),                  -- 공격자가 시도한 비밀번호
    input_command TEXT,                     -- 공격자가 입력한 명령어 (난독화 지시어 포함)
    country VARCHAR(50),                    -- 공격자 발원 국가 (GeoIP2)
    ai_label VARCHAR(100),                  -- AI 분석 의도 라벨 (코인채굴/봇넷 등)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()  -- DB 저장 일시
);