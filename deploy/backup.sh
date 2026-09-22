#!/usr/bin/env bash
# backup-s3.service 가 매일 04:00 에 돌림. 원본 로그만 올린다
# DB 는 백업 안 함. 원본 로그가 있으면 collector 를 다시 돌려 재구성 가능 (upsert 라 중복 없음)
set -euo pipefail

cd /opt/honeypot
: "${S3_BUCKET:?.env 에 S3_BUCKET 없음}"

aws s3 sync data/raw "s3://$S3_BUCKET/raw" --exclude "*.gz" --only-show-errors
