#!/usr/bin/env bash
# backup-s3.service 가 매일 04:00 에 돌림. 원본 로그 + Supabase 의 honeypot 스키마 덤프
set -euo pipefail

cd /opt/honeypot
: "${S3_BUCKET:?.env 에 S3_BUCKET 없음}"
: "${DATABASE_URL:?.env 에 DATABASE_URL 없음}"

aws s3 sync data/raw "s3://$S3_BUCKET/raw" --exclude "*.gz" --only-show-errors

# Free 플랜은 Supabase 자동 백업이 없다. pg_dump 는 서버(17)보다 같거나 새 버전이어야 함 (26.04 는 18)
dump="data/db-$(date -u +%F).sql.gz"
pg_dump "$DATABASE_URL" -n honeypot --no-owner --no-privileges | gzip > "$dump"
aws s3 cp "$dump" "s3://$S3_BUCKET/db/" --only-show-errors
find data -maxdepth 1 -name 'db-*.sql.gz' -mtime +3 -delete
