#!/usr/bin/env bash
# 분석 서버 (Ubuntu 26.04 arm64) 첫 세팅. DB 는 Supabase 라 여기엔 PostgreSQL 서버를 안 깐다
#   curl -fsSL https://raw.githubusercontent.com/ksj8i21/honeypot-capstone/main/deploy/bootstrap-analysis.sh -o b.sh
#   sudo bash b.sh https://github.com/ksj8i21/honeypot-capstone <팀원 GitHub 아이디...>
set -euo pipefail

REPO="${1:?저장소 URL}"; shift
APP=/opt/honeypot
ADMIN_PORT=62222
SSH_DROPIN=/etc/ssh/sshd_config.d/10-honeypot-admin.conf

[ "$(id -u)" -eq 0 ] || { echo "sudo 로 실행"; exit 1; }

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git python3-venv rsync awscli ssh-import-id

# 센서와 달리 22 를 넘길 일은 없지만 포트를 맞춰둬야 ~/.ssh/config 가 하나로 끝남.
# 24.04+ 는 ssh.socket 을 재시작해야 Port 가 반영된다
cat > "$SSH_DROPIN" <<EOF
Port 22
Port $ADMIN_PORT
PasswordAuthentication no
EOF
sshd -t
systemctl daemon-reload
systemctl restart ssh.socket 2>/dev/null || systemctl restart ssh

if [ ! -d "$APP/.git" ]; then
    git clone "$REPO" "$APP"
fi
chown -R ubuntu:ubuntu "$APP"
sudo -u ubuntu python3 -m venv "$APP/.venv"
[ -f "$APP/requirements.txt" ] && sudo -u ubuntu "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"
sudo -u ubuntu mkdir -p "$APP/data/raw/seoul" "$APP/data/raw/virginia"
chmod +x "$APP"/deploy/*.sh

if [ ! -f /home/ubuntu/.ssh/sensor_ro ]; then
    sudo -u ubuntu ssh-keygen -q -t ed25519 -N "" -f /home/ubuntu/.ssh/sensor_ro -C analysis-pull
fi

for gh in "$@"; do
    sudo -u ubuntu ssh-import-id-gh "$gh"
done

[ -f "$APP/.env" ] || { cp "$APP/.env.example" "$APP/.env"; chown ubuntu:ubuntu "$APP/.env"; chmod 600 "$APP/.env"; }

cat <<EOF

[분석 서버 기본 세팅 끝]
- 새 터미널에서 ssh -p $ADMIN_PORT 접속 확인 후 SG 에서 22 를 닫고 $SSH_DROPIN 의 'Port 22' 줄 삭제
- $APP/.env 채우기 (SUPABASE_URL, SUPABASE_SECRET_KEY, S3_BUCKET, 센서 IP ...)
- 센서 2대에 등록할 공개키:
$(cat /home/ubuntu/.ssh/sensor_ro.pub)
- 타이머는 ② 의 collector.run 이 main 에 올라온 뒤에: deploy/README.md 참고
EOF
