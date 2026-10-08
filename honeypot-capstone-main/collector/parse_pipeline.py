"""Cowrie JSON 로그를 Supabase 테이블(db/01_schema.sql)에 나눠 넣는다.

    python -m collector.parse_pipeline --sensor sample --dry-run
    python -m collector.parse_pipeline collector/samples/sample_cowrie.json --sensor sample
    python -m collector.parse_pipeline data/raw/seoul/cowrie.json --sensor seoul

키는 저장소 루트 .env 의 SUPABASE_URL, SUPABASE_SECRET_KEY 에서 읽는다.

TODO: 파일 오프셋 저장 (지금은 매번 처음부터 읽고 upsert 로 중복만 막음)
TODO: normalize.py 로 sessions.cmd_hash 채우기
"""

import argparse
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path

BATCH_SIZE = 500
DEFAULT_LOG = Path(__file__).parent / "samples" / "sample_cowrie.json"
EVENT_KEY = "sensor_id,session_id,eventid,ts"
SESSION_KEY = "sensor_id,session_id"

# (to_rows 결과 키, 테이블, on_conflict, ignore_duplicates)
# sessions 는 세 번에 나눠 보낸다. PostgREST upsert 는 한 요청 안의 컬럼 목록이 같아야 하고,
# 빠진 컬럼은 NULL 로 덮이기 때문에 connect / client.version / closed 를 한 행에 섞으면 start_ts 가 지워짐
UPLOAD_PLAN = [
    ("sessions_open", "sessions", SESSION_KEY, True),
    ("sessions_client", "sessions", SESSION_KEY, False),
    ("sessions_close", "sessions", SESSION_KEY, False),
    ("auth_attempts", "auth_attempts", EVENT_KEY, True),
    ("commands", "commands", EVENT_KEY, True),
    ("downloads", "downloads", EVENT_KEY, True),
]


def read_events(path: Path) -> tuple[list[dict], int]:
    events: list[dict] = []
    skipped = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                # Cowrie 가 쓰는 중인 마지막 줄은 잘려 있을 수 있음. 다음 실행 때 다시 읽힘
                skipped += 1
                continue
            if ev.get("session") and ev.get("timestamp") and ev.get("eventid"):
                events.append(ev)
            else:
                skipped += 1
    return events, skipped


def to_rows(events: list[dict], sensor_id: str) -> dict[str, list[dict]]:
    opened: dict[str, dict] = {}
    client: dict[str, dict] = {}
    closed: dict[str, dict] = {}
    rows: dict[str, list[dict]] = {"auth_attempts": [], "commands": [], "downloads": []}

    for ev in events:
        sid, eid, ts = ev["session"], ev["eventid"], ev["timestamp"]
        key = {"sensor_id": sensor_id, "session_id": sid}

        if eid == "cowrie.session.connect":
            opened[sid] = key | {
                "protocol": ev.get("protocol"),
                "src_ip": ev.get("src_ip"),
                "src_port": ev.get("src_port"),
                "start_ts": ts,
            }
        elif sid not in opened:
            # 로그를 중간부터 읽으면 connect 가 없다. 첫 이벤트로 세션 행만 만들어 둠 (protocol 은 비어 있음)
            opened[sid] = key | {"protocol": None, "src_ip": ev.get("src_ip"), "src_port": None, "start_ts": ts}

        if eid == "cowrie.client.version":
            client[sid] = key | {"client_version": ev.get("version")}
        elif eid == "cowrie.session.closed":
            closed[sid] = key | {"end_ts": ts, "duration": ev.get("duration")}
        elif eid in ("cowrie.login.success", "cowrie.login.failed"):
            rows["auth_attempts"].append(key | {
                "eventid": eid,
                "username": ev.get("username"),
                "password": ev.get("password"),
                "success": eid == "cowrie.login.success",
                "ts": ts,
            })
        elif eid in ("cowrie.command.input", "cowrie.command.failed"):
            rows["commands"].append(key | {"eventid": eid, "input": ev.get("input") or "", "ts": ts})
        elif eid == "cowrie.session.file_download":
            rows["downloads"].append(key | {
                "eventid": eid,
                "url": ev.get("url"),
                "shasum": ev.get("shasum"),
                "ts": ts,
            })

    # merge upsert 는 같은 요청에 같은 키가 두 번 있으면 에러라서 세션당 1행으로 모음
    rows["sessions_open"] = list(opened.values())
    rows["sessions_client"] = list(client.values())
    rows["sessions_close"] = list(closed.values())
    return rows


def chunks(items: list[dict], size: int = BATCH_SIZE) -> Iterator[list[dict]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def upload(rows: dict[str, list[dict]]) -> None:
    # dry-run 은 패키지 설치 없이 돌게 여기서 import
    from dotenv import load_dotenv
    from postgrest.types import ReturnMethod
    from supabase import create_client

    load_dotenv()
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])

    for name, table, on_conflict, ignore in UPLOAD_PLAN:
        for chunk in chunks(rows[name]):
            # 기본값 representation 이면 넣은 행을 전부 응답으로 돌려받아 Free 플랜 전송량을 씀
            sb.table(table).upsert(
                chunk,
                on_conflict=on_conflict,
                ignore_duplicates=ignore,
                returning=ReturnMethod.minimal,
            ).execute()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cowrie JSON 로그를 Supabase 에 적재")
    ap.add_argument("logfile", nargs="?", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--sensor", required=True, choices=["seoul", "virginia", "sample"],
                    help="sensors 테이블의 sensor_id")
    ap.add_argument("--dry-run", action="store_true", help="DB 에 넣지 않고 테이블별 행 수만 출력")
    args = ap.parse_args(argv)

    events, skipped = read_events(args.logfile)
    rows = to_rows(events, args.sensor)

    for name, _, _, _ in UPLOAD_PLAN:
        print(f"{name:<16} {len(rows[name])}")
    print(f"{'skipped lines':<16} {skipped}")

    if not args.dry_run:
        upload(rows)
        print("적재 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
