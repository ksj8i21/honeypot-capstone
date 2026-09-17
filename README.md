# honeypot-capstone

캡스톤디자인II 허니팟 프로젝트 저장소. Cowrie 센서 2대(서울/버지니아)의 로그를 분석 서버가 당겨와 Supabase 에 적재하고 Streamlit 으로 보여준다.

```
sensor/     ① 센서 설정 (docker-compose, cowrie.cfg, userdb.txt, setup.sh)
deploy/     ① 분석 서버 systemd 유닛, 자동 배포, 백업
aws/        ① AWS 콘솔/CLI 작업 순서
db/         ① Supabase 스키마·계정 / ② 테이블
collector/  ② ⑤
analyzer/   ③
dashboard/  ④
```

`.env`, `data/`, `*.mmdb` 는 절대 커밋하지 않는다. 센서 공인 IP 도 저장소에 적지 않는다.

센서 설정을 고쳤으면 push 전에:

```bash
python sensor/check_config.py
```
