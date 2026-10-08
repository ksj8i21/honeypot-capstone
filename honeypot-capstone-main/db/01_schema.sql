-- 테이블 (② 담당, 초안). Supabase SQL Editor 에서 실행
-- 접속은 supabase-py + secret 키(sb_secret_...). 키는 .env 에만
-- 다시 돌려도 안전하게 IF NOT EXISTS. 컬럼을 바꿀 땐 이 파일을 고치지 말고 02_... 로 ALTER 를 추가
--
-- db/capstone/schema.sql 의 honeypot_logs 컬럼이 어디로 갔는지
--   session_id, src_ip, timestamp  → sessions (start_ts) / 각 이벤트 테이블 ts
--   event_id                       → 각 이벤트 테이블 eventid
--   username, password             → auth_attempts
--   input_command                  → commands.input
--   country                        → geo (IP 당 1행)
--   ai_label                       → ai_analysis.intent (cmd_hash 당 1행)

CREATE TABLE IF NOT EXISTS public.sensors (
    sensor_id   TEXT PRIMARY KEY,            -- 'seoul', 'virginia', 샘플은 'sample'
    region      TEXT NOT NULL,
    deployed_at TIMESTAMPTZ
    -- 공인 IP 는 넣지 않는다. 키를 가진 사람 전원이 읽는 DB 라 노출 경로가 하나 더 생김
);

INSERT INTO public.sensors (sensor_id, region) VALUES
    ('seoul',    'ap-northeast-2'),
    ('virginia', 'us-east-1'),
    ('sample',   'local')
ON CONFLICT (sensor_id) DO NOTHING;


CREATE TABLE IF NOT EXISTS public.sessions (
    sensor_id      TEXT NOT NULL REFERENCES public.sensors (sensor_id),
    session_id     TEXT NOT NULL,
    protocol       TEXT CHECK (protocol IN ('ssh', 'telnet')),
    src_ip         INET,
    src_port       INTEGER,
    start_ts       TIMESTAMPTZ,
    end_ts         TIMESTAMPTZ,
    duration       REAL,                     -- 초. cowrie.session.closed 의 duration
    client_version TEXT,                     -- SSH 만. cowrie.client.version
    cmd_hash       TEXT,                     -- normalize.py 결과. 명령이 없으면 NULL
    PRIMARY KEY (sensor_id, session_id)
);


-- 이벤트 테이블은 sessions 에 FK 를 걸지 않는다.
-- 로그를 중간부터 읽으면 connect 이벤트 없이 로그인/명령이 먼저 올 수 있어서 insert 가 통째로 실패함

CREATE TABLE IF NOT EXISTS public.auth_attempts (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor_id  TEXT NOT NULL,
    session_id TEXT NOT NULL,
    eventid    TEXT NOT NULL,                -- cowrie.login.success / cowrie.login.failed
    username   TEXT,                         -- 길이 제한 없음. 페이로드가 계정 칸에 들어오기도 함
    password   TEXT,
    success    BOOLEAN NOT NULL,
    ts         TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_auth UNIQUE (sensor_id, session_id, eventid, ts)
);

CREATE TABLE IF NOT EXISTS public.commands (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor_id  TEXT NOT NULL,
    session_id TEXT NOT NULL,
    eventid    TEXT NOT NULL,                -- cowrie.command.input / cowrie.command.failed
    input      TEXT NOT NULL,
    ts         TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_cmd UNIQUE (sensor_id, session_id, eventid, ts)
);

CREATE TABLE IF NOT EXISTS public.downloads (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor_id  TEXT NOT NULL,
    session_id TEXT NOT NULL,
    eventid    TEXT NOT NULL,                -- cowrie.session.file_download 등
    url        TEXT,
    shasum     TEXT,
    ts         TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_dl UNIQUE (sensor_id, session_id, eventid, ts)
);


-- ⑤ enrich_geo.py 가 채움. IP 당 1행이라 이미 있으면 재조회 안 함
CREATE TABLE IF NOT EXISTS public.geo (
    src_ip       INET PRIMARY KEY,
    country_code CHAR(2),
    country      TEXT,
    city         TEXT,
    asn          INTEGER,
    org          TEXT,
    looked_up_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ③ 이 채움. 같은 cmd_hash 클러스터 전체가 이 한 행을 공유
CREATE TABLE IF NOT EXISTS public.ai_analysis (
    cmd_hash    TEXT PRIMARY KEY,
    intent      TEXT NOT NULL CHECK (intent IN ('코인채굴', '봇넷가담', '정찰', '자격증명탈취', '랜섬웨어', '기타')),
    severity    SMALLINT CHECK (severity BETWEEN 1 AND 5),
    summary     TEXT,
    ttp         TEXT[],
    model       TEXT,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE INDEX IF NOT EXISTS ix_sessions_proto_ts ON public.sessions (protocol, start_ts);
CREATE INDEX IF NOT EXISTS ix_sessions_cmdhash  ON public.sessions (cmd_hash);
CREATE INDEX IF NOT EXISTS ix_sessions_src_ip   ON public.sessions (src_ip);
CREATE INDEX IF NOT EXISTS ix_auth_session      ON public.auth_attempts (sensor_id, session_id);
CREATE INDEX IF NOT EXISTS ix_auth_user_pass    ON public.auth_attempts (username, password);
CREATE INDEX IF NOT EXISTS ix_commands_session  ON public.commands (sensor_id, session_id);


-- public 은 Data API 로 공개되는 스키마다. SQL 로 만든 테이블은 RLS 가 꺼진 채 생겨서
-- 공개된 publishable/anon 키만으로 읽기·쓰기·삭제가 된다.
-- 정책 없이 켜두면 anon 은 전부 막히고, secret 키(service_role)만 통과함
ALTER TABLE public.sensors       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.commands      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.downloads     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geo           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_analysis   ENABLE ROW LEVEL SECURITY;

-- 기존 테스트 테이블도 같이 막는다 (팀원 확인 후 DROP)
ALTER TABLE IF EXISTS public.honeypot_logs ENABLE ROW LEVEL SECURITY;
-- DROP TABLE IF EXISTS public.honeypot_logs;


-- 확인: RLS 꺼진 테이블이 하나도 안 나와야 함. 테이블을 새로 만들 때마다 다시 볼 것
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND NOT rowsecurity;


-- 적재 예시 (collector, supabase-py)
--
-- rows = [{"sensor_id": "seoul", "session_id": "...", "eventid": "cowrie.login.failed",
--          "username": "root", "password": "123", "success": False, "ts": "2026-09-17T10:00:02Z"}, ...]
-- sb.table("auth_attempts").upsert(rows, on_conflict="sensor_id,session_id,eventid,ts",
--                                  ignore_duplicates=True).execute()
--
-- 한 줄씩 insert 하지 말고 수백 행씩 묶어서. 같은 파일을 다시 넣어도 ignore_duplicates 로 행이 안 늘어남
-- 조회는 기본 1,000행에서 에러 없이 잘린다. 집계는 SQL 뷰나 함수로 만들고 .rpc() 로 부를 것
--
-- 샘플 데이터 정리 (실데이터 노출 직전):
-- DELETE FROM auth_attempts WHERE sensor_id = 'sample';   -- commands, downloads, sessions 도 동일
