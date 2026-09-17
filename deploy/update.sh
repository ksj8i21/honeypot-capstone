#!/usr/bin/env bash
# 분석 서버에서 실행. origin/main 을 운영본에 강제로 맞춘다.
set -euo pipefail

cd /opt/honeypot

before=$(git rev-parse HEAD)
git fetch --quiet origin main
after=$(git rev-parse origin/main)

# 변경이 없으면 대시보드를 건드리지 않는다. 주기마다 재시작되면 쓸 수가 없음
if [ "$before" = "$after" ]; then
    exit 0
fi

# 서버는 편집 금지지만 누가 건드렸을 수 있다. 버리되 무엇을 버렸는지는 남긴다
if ! git diff --quiet HEAD; then
    echo "서버 로컬 변경을 버림:"
    git status --short
fi

git reset --hard "$after" --quiet

.venv/bin/pip install -q -r requirements.txt

# collector·analyzer 는 oneshot 이라 다음 타이머 실행 때 새 코드로 돈다. 대시보드만 재시작
sudo systemctl restart honeypot-dashboard

echo "배포 $(git log -1 --oneline)"
