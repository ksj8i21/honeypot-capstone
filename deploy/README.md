# deploy — 분석 서버 유닛

분석 서버에서만 씁니다. 센서 쪽 파일은 `sensor/` 에 있습니다.
DB 는 Supabase 입니다. 분석 서버에는 PostgreSQL 서버를 설치하지 않고 `postgresql-client`(pg_dump 용)만 둡니다.

## 처음 한 번

```bash
sudo bash deploy/bootstrap-analysis.sh <저장소 URL> <팀원 GitHub 아이디> ...
```

패키지, 관리 SSH 62222, `/opt/honeypot` clone, venv, `data/raw/{seoul,virginia}`, 센서 Pull 키(`~/.ssh/sensor_ro`), 팀원 공개키 등록까지 합니다.
끝나면 `/opt/honeypot/.env` 를 채웁니다. 키 이름은 `.env.example` 참고.

## 타이머 켜기 (②의 collector.run 이 main 에 올라온 뒤)

```bash
sudo cp deploy/*.service deploy/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now honeypot-collector.timer honeypot-analyzer.timer \
                            backup-s3.timer honeypot-update.timer \
                            honeypot-dashboard.service
```

`.timer` 만 enable 합니다. oneshot 서비스를 enable 하면 부팅 때 한 번 돌고 끝납니다. 상시 실행인 대시보드만 예외입니다.

`ExecStart` 의 모듈 경로(`collector.run`, `analyzer.run_nightly`)는 ②③ 이 실제로 만든 진입점 이름에 맞춰 고칩니다.

## 주기

| 유닛 | 주기 | 하는 일 |
|---|---|---|
| honeypot-collector | 1시간 (앞 실행 종료 기준) | 센서 2대 Pull → 파싱 → Supabase 적재 → GeoIP |
| honeypot-analyzer | 매일 03:00 | AI 배치 |
| backup-s3 | 매일 04:00 | 원본 로그 sync + honeypot 스키마 pg_dump → S3 |
| honeypot-update | 5분 | origin/main 자동 배포 |
| honeypot-dashboard | 상시 | Streamlit (127.0.0.1:8501) |

DB 덤프를 백업에 넣은 건 Supabase Free 플랜에 자동 백업이 없어서입니다. Pro 로 가면 빼도 됩니다.

## 자동 배포

`update.sh` 가 5분마다 origin/main 을 보고, 새 커밋이 있을 때만 `git reset --hard` + 의존성 설치 + 대시보드 재시작을 합니다.
서버에서 코드를 직접 고치면 다음 주기에 사라집니다. 시험은 자기 홈에 따로 clone 해서.

발표 당일과 리허설 중에는 끕니다.

```bash
sudo systemctl stop honeypot-update.timer
```

## 확인

```bash
systemctl list-timers | grep honeypot
journalctl -u honeypot-collector -f
journalctl -u honeypot-update -n 30
sudo systemctl start backup-s3.service && journalctl -u backup-s3 -n 20
```
