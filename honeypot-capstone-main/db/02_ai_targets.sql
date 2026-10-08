-- =============================================================================
-- 02_ai_targets.sql
-- 
-- AI 분석 대상 세션(고유 명령 패턴 cmd_hash)을 선별하는 SQL 함수입니다.
-- 
-- 주요 조건 및 특징:
--  1. cmd_hash가 존재하는 세션만 대상으로 함
--  2. auth_attempts 테이블에서 로그인 성공(success = true) 이력이 있는 세션만 선별
--  3. 이미 ai_analysis 테이블에 분석 결과가 존재하는 cmd_hash는 제외
--  4. 동일한 cmd_hash를 가진 세션 중 가장 먼저 발생한 세션 1개(rn = 1)를 대표로 추출
--  5. 해당 세션의 명령어 목록(commands.input)을 개행문자('\n')로 합쳐서 반환
--  6. 빈도수가 높은(cluster_size가 큰) 패턴 순으로 정렬하여 하루 max_rows 상한만큼 제한
-- =============================================================================

CREATE OR REPLACE FUNCTION public.pick_ai_targets(max_rows integer DEFAULT 150)
RETURNS TABLE (
    cmd_hash text,
    protocol text,
    sensor_id text,
    session_id text,
    commands text,
    cluster_size bigint
)
LANGUAGE sql STABLE
AS $$
    WITH candidates AS (
        SELECT 
            s.cmd_hash, 
            s.protocol, 
            s.sensor_id, 
            s.session_id, 
            s.start_ts
        FROM public.sessions s
        WHERE s.cmd_hash IS NOT NULL
          AND EXISTS (
              SELECT 1 
              FROM public.auth_attempts a
              WHERE a.sensor_id = s.sensor_id
                AND a.session_id = s.session_id
                AND a.success = true
          )
          AND NOT EXISTS (
              SELECT 1 
              FROM public.ai_analysis x 
              WHERE x.cmd_hash = s.cmd_hash
          )
    ),
    ranked AS (
        SELECT 
            c.*,
            count(*) OVER (PARTITION BY c.cmd_hash) AS cluster_size,
            row_number() OVER (PARTITION BY c.cmd_hash ORDER BY c.start_ts) AS rn
        FROM candidates c
    )
    SELECT 
        r.cmd_hash, 
        r.protocol, 
        r.sensor_id, 
        r.session_id,
        (
            SELECT string_agg(m.input, E'\n' ORDER BY m.ts)
            FROM public.commands m
            WHERE m.sensor_id = r.sensor_id 
              AND m.session_id = r.session_id
        ) AS commands,
        r.cluster_size
    FROM ranked r
    WHERE r.rn = 1
    ORDER BY r.cluster_size DESC
    LIMIT max_rows;
$$;

-- 보안 설정: 익명(anon) 및 일반 인증 사용자(authenticated)의 직접 호출을 제한하고,
-- service_role (secret 키)만 실행할 수 있도록 권한을 박탈합니다.
REVOKE EXECUTE ON FUNCTION public.pick_ai_targets(integer) FROM public, anon, authenticated;