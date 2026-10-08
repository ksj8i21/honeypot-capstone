-- Supabase SQL Editor 에서 1회 실행 (① 담당). 테이블은 ② 가 01_schema.sql 로 이 스키마 안에 만든다
-- 실행 전 두 비밀번호를 바꾸고, 바꾼 값은 이 파일에 저장하지 말 것

-- public 은 Data API(anon 키)로 외부 노출되는 스키마라 쓰지 않는다.
-- 새 스키마는 Settings → Data API → Exposed schemas 에 추가하지 않는 한 API 로 안 보임
CREATE SCHEMA IF NOT EXISTS honeypot;
REVOKE ALL ON SCHEMA honeypot FROM anon, authenticated, public;

-- 수집기·AI 배치용 (쓰기)
CREATE ROLE hp_writer LOGIN PASSWORD 'CHANGE_ME_WRITER';
-- 대시보드·통계용 (읽기만). 팀원 PC 에서 붙을 때도 기본은 이 계정
CREATE ROLE hp_reader LOGIN PASSWORD 'CHANGE_ME_READER';

-- 테이블 DDL 은 SQL Editor(postgres)에서만 돌린다. hp_writer 에는 CREATE 를 안 줌
GRANT USAGE ON SCHEMA honeypot TO hp_writer, hp_reader;

ALTER ROLE hp_writer SET search_path = honeypot, public;
ALTER ROLE hp_reader SET search_path = honeypot, public;

-- 앞으로 postgres 가 만들 테이블에 자동 적용
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA honeypot
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hp_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA honeypot
    GRANT USAGE, SELECT ON SEQUENCES TO hp_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA honeypot
    GRANT SELECT ON TABLES TO hp_reader;

-- 이 파일보다 ② 의 테이블이 먼저 생겼으면 아래도 필요 (다시 돌려도 무해)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA honeypot TO hp_writer;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA honeypot TO hp_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA honeypot TO hp_reader;

-- 대시보드 실수로 무거운 쿼리가 커넥션을 오래 잡지 않게
ALTER ROLE hp_reader SET statement_timeout = '30s';

-- 확인
-- SELECT rolname FROM pg_roles WHERE rolname LIKE 'hp_%';
-- 접속 문자열 사용자명은 풀러 경유라 hp_writer.<project-ref> 형식
