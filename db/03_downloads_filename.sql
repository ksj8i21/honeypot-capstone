-- downloads 에 SCP 업로드(cowrie.session.file_upload)와 받기 실패(cowrie.session.file_download.failed)도 넣으면서 추가
-- filename = 업로드는 공격자가 붙인 이름(sshd 등), 다운로드는 공격자가 저장한 경로. 실패 행은 NULL
-- 이 파일을 먼저 실행한 뒤에 collector 코드를 올릴 것. 칸이 없으면 적재가 통째로 실패함
ALTER TABLE public.downloads ADD COLUMN IF NOT EXISTS filename TEXT;
