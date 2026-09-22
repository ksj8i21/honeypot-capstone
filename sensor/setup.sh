#!/usr/bin/env bash
# 센서 EC2 (Ubuntu 26.04 arm64) 에서 실행. 저장소를 홈에 clone 한 뒤:
#   sudo ./sensor/setup.sh base        패키지 + 관리 SSH 62222 추가 (22 도 아직 열려 있음)
#   ── 여기서 새 터미널로 ssh -p 62222 접속되는지 직접 확인 ──
#   sudo ./sensor/setup.sh cowrie      sshd 에서 22 제거 → Cowrie 가 22/23 을 받음
#   sudo ./sensor/setup.sh pullkey 'ssh-ed25519 AAAA... analysis-pull'
#   sudo ./sensor/setup.sh pullkey-lock 'ssh-ed25519 AAAA... analysis-pull'
#   sudo ./sensor/setup.sh ami-clean   AMI 뜨기 직전 (버지니아 복사용)
set -euo pipefail

COWRIE_DIR=/opt/cowrie
ADMIN_PORT=62222
SSH_DROPIN=/etc/ssh/sshd_config.d/10-honeypot-admin.conf
AUTH_KEYS=/home/ubuntu/.ssh/authorized_keys
HERE="$(cd "$(dirname "$0")" && pwd)"

die() { echo "!! $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "sudo 로 실행"

# 24.04 부터 ssh.socket 이 포트를 잡는다. restart ssh 만 하면 Port 를 바꿔도 반영이 안 됨
reload_sshd() {
    sshd -t
    systemctl daemon-reload
    if systemctl is-active --quiet ssh.socket; then
        systemctl restart ssh.socket
    else
        systemctl restart ssh
    fi
    sleep 1
}

listening() { ss -Htln "sport = :$1" | grep -q .; }

step_base() {
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 rsync
    usermod -aG docker ubuntu

    # 22 를 같이 남기는 건 62222 가 안 붙었을 때 들어올 길을 남기려고
    cat > "$SSH_DROPIN" <<EOF
Port 22
Port $ADMIN_PORT
PasswordAuthentication no
EOF
    reload_sshd
    listening "$ADMIN_PORT" || die "sshd 가 $ADMIN_PORT 에서 안 뜸. $SSH_DROPIN 확인"

    cat <<EOF

[base 완료]
1. SG 인바운드에 $ADMIN_PORT (내 IP) 가 있는지 확인
2. 지금 세션은 닫지 말고, 새 터미널에서:  ssh -p $ADMIN_PORT ubuntu@<센서IP>
3. 붙으면 그 새 세션에서:  sudo ./sensor/setup.sh cowrie
EOF
}

step_cowrie() {
    listening "$ADMIN_PORT" || die "$ADMIN_PORT 가 안 열려 있음. base 먼저"

    sed -i '/^Port 22$/d' "$SSH_DROPIN"
    reload_sshd
    listening 22 && die "sshd 가 아직 22 를 잡고 있음. /etc/ssh/sshd_config 의 Port 줄 확인"

    install -d -m 755 "$COWRIE_DIR"
    install -d -m 755 -o 999 -g 999 \
        "$COWRIE_DIR/var" "$COWRIE_DIR/var/log/cowrie" "$COWRIE_DIR/var/lib/cowrie"
    rm -rf "$COWRIE_DIR/etc"
    cp -r "$HERE/etc" "$COWRIE_DIR/etc"
    cp "$HERE/docker-compose.yml" "$COWRIE_DIR/"

    (cd "$COWRIE_DIR" && docker compose pull && docker compose up -d)

    for _ in $(seq 20); do listening 22 && listening 23 && break; sleep 3; done
    listening 22 && listening 23 || { docker logs cowrie --tail 40; die "Cowrie 가 22/23 에 안 뜸"; }

    install -m 644 "$HERE/cowrie-logclean.service" "$HERE/cowrie-logclean.timer" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now cowrie-logclean.timer

    echo "[cowrie 완료] 배너: $(timeout 3 bash -c "exec 3<>/dev/tcp/127.0.0.1/22; head -c 60 <&3" || true)"
    echo "밖에서 ssh root@<센서IP> / telnet <센서IP> 로 가짜 셸이 뜨는지 확인"
}

# 처음엔 제한 없이 등록해서 SG·키·경로 중 무엇이 문제인지 가른다. 되면 pullkey-lock
add_pull_key() {
    local key="$1" opts="$2"
    [[ "$key" == ssh-ed25519\ * ]] || die "공개키 한 줄 전체를 따옴표로 넘길 것"
    local body; body="$(awk '{print $2}' <<<"$key")"
    install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/.ssh
    touch "$AUTH_KEYS"
    sed -i "\|$body|d" "$AUTH_KEYS"
    echo "${opts:+$opts }$key" >> "$AUTH_KEYS"
    chown ubuntu:ubuntu "$AUTH_KEYS"; chmod 600 "$AUTH_KEYS"
}

step_pullkey() {
    add_pull_key "$1" ""
    sudo -u ubuntu test -r "$COWRIE_DIR/var/log/cowrie/cowrie.json" \
        || echo "?? ubuntu 가 cowrie.json 을 못 읽음. 아직 접속이 한 번도 없었거나 권한 문제"
    echo "분석 서버에서: rsync -az -e 'ssh -p $ADMIN_PORT -i ~/.ssh/sensor_ro' ubuntu@<센서IP>:$COWRIE_DIR/var/log/cowrie/ data/raw/<리전>/"
}

step_pullkey_lock() {
    add_pull_key "$1" "command=\"/usr/bin/rrsync -ro $COWRIE_DIR/var/log/cowrie\",restrict"
    echo "제한 적용됨. 이제 원격 경로는 루트:  ubuntu@<센서IP>:/"
}

step_ami_clean() {
    (cd "$COWRIE_DIR" && docker compose down)
    # 서울 로그가 버지니아 쪽에 섞이고, 같은 호스트 키면 스캐너가 같은 운영자로 묶음
    rm -rf "$COWRIE_DIR"/var/log/cowrie/* "$COWRIE_DIR"/var/lib/cowrie/*
    echo "이 상태로 AMI 생성. 서울 센서는 다시 올릴 것: cd $COWRIE_DIR && sudo docker compose up -d"
    echo "버지니아 인스턴스에서도 첫 기동 후 docker compose up -d (호스트 키는 Cowrie 가 새로 만듦)"
}

case "${1:-}" in
    base)         step_base ;;
    cowrie)       step_cowrie ;;
    pullkey)      step_pullkey "${2:?공개키}" ;;
    pullkey-lock) step_pullkey_lock "${2:?공개키}" ;;
    ami-clean)    step_ami_clean ;;
    *) sed -n '2,9p' "$0"; exit 1 ;;
esac
