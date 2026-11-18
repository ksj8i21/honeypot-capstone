-- 대시보드(dashboard/data.py)가 부르는 집계 함수. 함수 이름·칼럼 이름이 data.py 와 맞아야 화면에 실제 값이 나온다
-- get_country_distribution, get_top_auth_attempts, get_time_patterns 는 11-18 라이브 DB 에 있던 정의 그대로 옮긴 것 (저장소에는 없었음)
-- 시각은 전부 한국 시간(KST) 기준, 기간 제한 없이 수집 전체를 센다
--
-- 호출: sb.rpc("get_overview").execute().data

CREATE OR REPLACE FUNCTION public.get_overview()
RETURNS TABLE (total_sessions bigint, unique_ips bigint, first_ts timestamptz, last_ts timestamptz)
LANGUAGE sql STABLE
AS $$
    SELECT count(*), count(DISTINCT src_ip), min(start_ts), max(start_ts)
    FROM public.sessions
    WHERE sensor_id <> 'sample'
$$;

CREATE OR REPLACE FUNCTION public.get_country_distribution()
RETURNS TABLE (country_code character, country text, attempts bigint)
LANGUAGE sql STABLE
AS $$
    SELECT g.country_code, g.country, count(s.session_id) AS attempts
    FROM public.sessions s
    LEFT JOIN public.geo g ON s.src_ip = g.src_ip
    GROUP BY g.country_code, g.country
    ORDER BY attempts DESC
$$;

CREATE OR REPLACE FUNCTION public.get_top_auth_attempts()
RETURNS TABLE (username text, password text, attempts bigint)
LANGUAGE sql STABLE
AS $$
    SELECT username, password, count(*) AS attempts
    FROM public.auth_attempts
    GROUP BY username, password
    ORDER BY attempts DESC
    LIMIT 10
$$;

CREATE OR REPLACE FUNCTION public.get_time_patterns()
RETURNS TABLE (day_of_week text, hour_of_day integer, attempts bigint)
LANGUAGE sql STABLE
AS $$
    SELECT to_char(start_ts AT TIME ZONE 'Asia/Seoul', 'Day'),
           extract(hour FROM start_ts AT TIME ZONE 'Asia/Seoul')::int,
           count(*)
    FROM public.sessions
    GROUP BY 1, 2
$$;

CREATE OR REPLACE FUNCTION public.get_hourly_by_protocol()
RETURNS TABLE (protocol text, hour_of_day integer, sessions bigint)
LANGUAGE sql STABLE
AS $$
    SELECT protocol, extract(hour FROM start_ts AT TIME ZONE 'Asia/Seoul')::int, count(*)
    FROM public.sessions
    WHERE protocol IS NOT NULL AND start_ts IS NOT NULL
    GROUP BY 1, 2
$$;

-- 칼럼이 늘어서(avg_commands, success_rate) CREATE OR REPLACE 로는 안 바뀐다. 지우고 다시 만든다
-- avg_commands = 명령(input) 수 / 세션 수, success_rate = 로그인 시도 중 성공한 비율(%)
-- 11-18 실측: ssh 0.03개·2.5%, telnet 14.02개·52.3%. commands 115만 행 조인이라 SQL Editor 에서 3.3초
DROP FUNCTION IF EXISTS public.get_protocol_stats();
CREATE FUNCTION public.get_protocol_stats()
RETURNS TABLE (protocol text, sessions bigint, avg_duration real, avg_commands float8, success_rate float8)
LANGUAGE sql STABLE
AS $$
    WITH s AS (
        SELECT protocol, count(*) AS sessions, avg(duration)::real AS avg_duration
        FROM public.sessions
        WHERE protocol IS NOT NULL
        GROUP BY protocol
    ), c AS (
        SELECT s.protocol, count(*) AS n
        FROM public.commands c
        JOIN public.sessions s USING (sensor_id, session_id)
        WHERE c.eventid = 'cowrie.command.input'
        GROUP BY s.protocol
    ), a AS (
        SELECT s.protocol, count(*) AS tries, count(*) FILTER (WHERE a.success) AS ok
        FROM public.auth_attempts a
        JOIN public.sessions s USING (sensor_id, session_id)
        GROUP BY s.protocol
    )
    SELECT s.protocol, s.sessions, s.avg_duration,
           coalesce(c.n, 0)::float8 / s.sessions,
           coalesce(round(100.0 * a.ok / nullif(a.tries, 0), 1), 0)::float8
    FROM s
    LEFT JOIN c USING (protocol)
    LEFT JOIN a USING (protocol)
$$;

-- 텔넷 봇이 로그인 창에 보낸 enable\x00·system\x00·shell\x00 이 계정 3~4위로 올라와서(11-18 enable\x00 5,829건)
-- \x.. 가 섞인 값은 순위에서 뺀다 (정규식에 역슬래시를 직접 쓰면 붙여넣는 경로마다 개수가 달라져서 chr(92) 로 씀). 빈 비밀번호('')는 실제 시도라 남긴다 (텔넷 2위, 1,491건)
CREATE OR REPLACE FUNCTION public.get_auth_usernames(p_protocol text)
RETURNS TABLE (item text, attempts bigint)
LANGUAGE sql STABLE
AS $$
    SELECT a.username, count(*)
    FROM public.auth_attempts a
    JOIN public.sessions s USING (sensor_id, session_id)
    WHERE s.protocol = p_protocol
      AND a.username IS NOT NULL AND a.username <> ''
      AND a.username !~ (chr(92) || chr(92) || 'x[0-9a-fA-F]{2}')
    GROUP BY a.username
    ORDER BY count(*) DESC, a.username
    LIMIT 10
$$;

CREATE OR REPLACE FUNCTION public.get_auth_passwords(p_protocol text)
RETURNS TABLE (item text, attempts bigint)
LANGUAGE sql STABLE
AS $$
    SELECT a.password, count(*)
    FROM public.auth_attempts a
    JOIN public.sessions s USING (sensor_id, session_id)
    WHERE s.protocol = p_protocol
      AND a.password IS NOT NULL
      AND a.password !~ (chr(92) || chr(92) || 'x[0-9a-fA-F]{2}')
    GROUP BY a.password
    ORDER BY count(*) DESC, a.password
    LIMIT 10
$$;

-- 명령을 친 세션을 AI 판정별로 센다. intent 가 NULL 인 행 = 아직 분석 전(분석 대기)
-- 예전 정의는 ai_analysis 의 패턴 수만 세고 프로토콜이 없었다. 칼럼이 바뀌어 지우고 다시 만든다
DROP FUNCTION IF EXISTS public.get_ai_threat_summary();
CREATE FUNCTION public.get_ai_threat_summary()
RETURNS TABLE (intent text, severity smallint, protocol text, cnt bigint)
LANGUAGE sql STABLE
AS $$
    SELECT a.intent, a.severity, s.protocol, count(*)
    FROM public.sessions s
    LEFT JOIN public.ai_analysis a ON a.cmd_hash = s.cmd_hash
    WHERE s.cmd_hash IS NOT NULL
      AND s.sensor_id <> 'sample'
    GROUP BY 1, 2, 3
$$;

REVOKE EXECUTE ON FUNCTION public.get_overview() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_country_distribution() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_top_auth_attempts() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_time_patterns() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_hourly_by_protocol() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_protocol_stats() FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_auth_usernames(text) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_auth_passwords(text) FROM public, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_ai_threat_summary() FROM public, anon, authenticated;

-- API 기본 제한은 8초. Streamlit Cloud 배포 직후 첫 호출이 여기에 걸려 예시 데이터가 나왔다 (11-18 23:42 Postgres 로그에 statement timeout 4번)
-- 함수에 걸어 둔 statement_timeout 은 PostgREST 가 호출할 때 그대로 적용한다
ALTER FUNCTION public.get_overview() SET statement_timeout TO '30s';
ALTER FUNCTION public.get_country_distribution() SET statement_timeout TO '30s';
ALTER FUNCTION public.get_top_auth_attempts() SET statement_timeout TO '30s';
ALTER FUNCTION public.get_time_patterns() SET statement_timeout TO '30s';
ALTER FUNCTION public.get_hourly_by_protocol() SET statement_timeout TO '30s';
ALTER FUNCTION public.get_protocol_stats() SET statement_timeout TO '30s';
ALTER FUNCTION public.get_auth_usernames(text) SET statement_timeout TO '30s';
ALTER FUNCTION public.get_auth_passwords(text) SET statement_timeout TO '30s';
ALTER FUNCTION public.get_ai_threat_summary() SET statement_timeout TO '30s';
