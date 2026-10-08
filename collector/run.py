"""collector 메인 진입점 (python -m collector.run)

서버가 1시간마다 부르는 수집 총괄 스크립트.
data/raw/seoul/, data/raw/virginia/ 폴더 안의 Cowrie 로그를 오프셋(State) 기반으로 읽어
parse_pipeline으로 DB 적재 후, 마지막에 enrich_geo.run(sb)을 호출한다.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

from collector.parse_pipeline import to_rows, upload

# 오프셋 상태 저장 파일
STATE_FILE = Path("data/collector_state.json")


def read_events_from_offset(path: Path, start_offset: int = 0) -> tuple[list[dict], int, int]:
    """오프셋 기반으로 파일의 새로운 줄만 읽어오는 함수"""
    events: list[dict] = []
    skipped = 0
    current_offset = start_offset

    with path.open("rb") as f:
        # 파일 크기가 기존 저장 위치보다 작아졌으면 (파일 로테이션 발생) 처음부터 읽음
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        if file_size < start_offset:
            start_offset = 0

        f.seek(start_offset)

        while True:
            line_bytes = f.readline()
            if not line_bytes:
                break

            # 마지막 줄이 완전히 기록되지 않고 잘려있으면 다음 회차로 미룸
            if not line_bytes.endswith(b"\n") and not line_bytes.endswith(b"\r"):
                break

            current_offset = f.tell()
            line_str = line_bytes.decode("utf-8", errors="ignore").strip()
            if not line_str:
                continue

            try:
                ev = json.loads(line_str)
            except json.JSONDecodeError:
                skipped += 1
                continue

            if ev.get("session") and ev.get("timestamp") and ev.get("eventid"):
                events.append(ev)
            else:
                skipped += 1

    return events, skipped, current_offset


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

    # 오프셋 상태 파일 불러오기
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    # 센서 폴더 탐색 (seoul, virginia)
    for sensor_dir in data_raw.iterdir():
        if sensor_dir.is_dir():
            sensor_id = sensor_dir.name  # seoul, virginia
            for log_file in sensor_dir.glob("cowrie.json*"):
                if log_file.is_file():
                    file_key = str(log_file)
                    last_offset = state.get(file_key, 0)

                    events, skipped, new_offset = read_events_from_offset(log_file, last_offset)
                    state[file_key] = new_offset

                    if events:
                        rows = to_rows(events, sensor_id)
                        upload(rows)
                        print(f"[SUCCESS] 센서={sensor_id}, 파일={log_file.name}: {len(events)}개 새 이벤트 적재 완료 (오프셋: {last_offset}->{new_offset}, skipped: {skipped})")

    # 오프셋 상태 파일 저장
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

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
