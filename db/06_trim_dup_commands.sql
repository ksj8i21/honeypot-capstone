-- 11-12 commands 에서 정보 없는 행 155,773개를 지웠다. DB 465.5 → 388.5MiB (대시보드 487 → 407MB)
-- 빈 명령 26,851 + 같은 줄 input 0.01초 뒤에 또 찍힌 failed 128,922. 짝 없는 failed 27,323행은 스크립트 속 하위 명령(./dvrHelper selfrep 등)이라 남김
-- collector/parse_pipeline.py 도 같은 기준으로 안 넣게 바꿨다. 그 코드가 배포되기 전에 들어온 행은 이 DELETE 를 한 번 더 돌리면 빠진다
-- 원본은 분석 서버 raw 로그와 S3 에 그대로 있음
SET lock_timeout = '3s';
DELETE FROM public.commands c
 WHERE btrim(c.input, E' \t\r\n\f\v') = ''
    OR (c.eventid = 'cowrie.command.failed' AND EXISTS (
          SELECT 1 FROM public.commands i
           WHERE i.sensor_id = c.sensor_id AND i.session_id = c.session_id
             AND i.eventid = 'cowrie.command.input'
             AND i.ts BETWEEN c.ts - interval '2 seconds' AND c.ts + interval '2 seconds'
             AND btrim(i.input, E' \t\r\n\f\v') = btrim(c.input, E' \t\r\n\f\v')));

-- DELETE 만으론 크기가 그대로라 처음 한 번은 아래를 따로 돌렸다 (28초, 그동안 commands 잠김)
-- 같이 실행하면 'cannot run inside a transaction block' 이 나니까 이 줄만 선택해서 실행. uq_cmd 가 140.6 → 80.9MiB 로 줄어든 게 절반 넘게 차지함
-- VACUUM (FULL, ANALYZE) public.commands;
