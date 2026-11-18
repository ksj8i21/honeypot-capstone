-- 11-11 DB 가 506/500MB 로 Free 한도를 넘어서 겹치는 인덱스 둘을 뺐다. 지운 뒤 487MB
-- 둘 다 uq_cmd·uq_auth 의 앞 두 칼럼과 같아서 세션 단위 조회는 uq 쪽을 탄다 (지운 뒤 EXPLAIN 으로 봄)
-- collector 가 쓰는 중이면 잠금을 못 잡고 3초 뒤 실패하니 그때는 다시 실행
SET lock_timeout = '3s';
DROP INDEX IF EXISTS public.ix_commands_session;
DROP INDEX IF EXISTS public.ix_auth_session;
