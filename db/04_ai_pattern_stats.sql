-- 공격 패턴(cmd_hash)별 한 줄: AI 판정 + 세션 수·IP 수·센서·프로토콜·처음/마지막 시각. ④ AI 페이지, ⑤ 통계용
-- ai_analysis 에 IP 칸을 안 둔 이유: 패턴 하나를 여러 IP 가 같이 씀 (10-08 1위 패턴 = 세션 678·IP 3, 5위 = 세션 68·IP 68)
-- 아직 AI 분석 전인 패턴은 intent 가 NULL 로 나옴 → 화면에는 "분석 대기"
--
-- 호출: sb.rpc("ai_pattern_stats", {"max_rows": 200}).execute().data

CREATE OR REPLACE FUNCTION public.ai_pattern_stats(max_rows integer DEFAULT 200)
RETURNS TABLE (
    cmd_hash     text,
    intent       text,
    severity     smallint,
    summary      text,
    ttp          text[],
    sessions     bigint,
    distinct_ips bigint,
    sensors      text[],
    protocols    text[],
    first_seen   timestamptz,
    last_seen    timestamptz
)
LANGUAGE sql STABLE
AS $$
    SELECT
        s.cmd_hash,
        a.intent,
        a.severity,
        a.summary,
        a.ttp,
        count(*),
        count(DISTINCT s.src_ip),
        array_agg(DISTINCT s.sensor_id),
        array_agg(DISTINCT s.protocol),
        min(s.start_ts),
        max(s.start_ts)
    FROM public.sessions s
    LEFT JOIN public.ai_analysis a ON a.cmd_hash = s.cmd_hash
    WHERE s.cmd_hash IS NOT NULL
      AND s.sensor_id <> 'sample'
    GROUP BY s.cmd_hash, a.intent, a.severity, a.summary, a.ttp
    ORDER BY count(*) DESC
    LIMIT max_rows
$$;

REVOKE EXECUTE ON FUNCTION public.ai_pattern_stats(integer) FROM public, anon, authenticated;
