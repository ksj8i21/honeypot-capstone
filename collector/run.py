"""collector 메인 진입점 (python -m collector.run)

서버가 1시간마다 부르는 수집 총괄 스크립트.
data/raw/seoul/, data/raw/virginia/ 폴더 안의 Cowrie 로그를 읽어
parse_pipeline으로 DB 적재 후, 마지막에 enrich_geo.run(sb)을 호출한다.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

from collector.parse_pipeline import read_events, to_rows, upload
from collector.normalize import compute_cmd_hash

# 상태 저장 파일 (오프셋 포인터)
STATE_FILE = Path("data/collector_state.json")


def run_collection():
    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        print("[ERROR] SUPABASE_URL 또는 SUPABASE_SECRET_KEY가 .env에 설정되지 않았습니다.")
        return

    sb = create_client(url, key)

    # 데이터 폴더 기본 경로
    data_raw = Path("data/raw")
    if not data_raw.exists():
        data_raw = Path("/opt/honeypot/data/raw")

    if not data_raw.exists():
        print(f"[WARN] raw 데이터 폴더를 찾을 수 없습니다: {data_raw}")
        return

    # 센서 폴더 탐색 (seoul, virginia)
    for sensor_dir in data_raw.iterdir():
        if sensor_dir.is_dir():
            sensor_id = sensor_dir.name  # seoul, virginia
            for log_file in sensor_dir.glob("cowrie.json*"):
                if log_file.is_file():
                    print(f"[INFO] 로그 적재 시작: 센서={sensor_id}, 파일={log_file.name}")
                    events, skipped = read_events(log_file)
                    if events:
                        rows = to_rows(events, sensor_id)
                        upload(rows)
                        print(f"[SUCCESS] {len(events)}개 이벤트 적재 완료 (skipped: {skipped})")

    # 매시간 마지막에 GeoIP 위치 채우기 부르기 (팀 가이드 [정해진 것] 5번)
    try:
        from collector import enrich_geo
        if hasattr(enrich_geo, "run"):
            count = enrich_geo.run(sb)
            print(f"[INFO] GeoIP 국가 보강 완료: {count}개 IP 업데이트")
    except (ImportError, Exception) as e:
        print(f"[INFO] GeoIP 보강 스킵 (enrich_geo 준비 중 또는 mmdb 없음): {e}")


if __name__ == "__main__":
    run_collection()
