"""분석 대상 고르기 (작업가이드 4-1). 조건은 db/02_ai_targets.sql 의 pick_ai_targets 함수에 있음.

    python -m analyzer.filter          # 상위 10건 미리보기 (DB 만 읽음, API 호출 없음)
"""

import os
from typing import Any

from supabase import Client


def pick_targets(sb: Client, max_rows: int) -> list[dict[str, Any]]:
    rows = sb.rpc("pick_ai_targets", {"max_rows": max_rows}).execute().data or []
    # cmd_hash 는 있는데 commands 행이 없는 세션은 보낼 내용이 없음
    targets = [r for r in rows if r.get("cmd_hash") and str(r.get("commands") or "").strip()]
    if len(targets) < len(rows):
        print(f"[filter] 명령이 비어 있는 대상 {len(rows) - len(targets)}건 제외")
    print(f"[filter] 분석 대상 {len(targets)}건")
    return targets


if __name__ == "__main__":
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    for t in pick_targets(sb, max_rows=10):
        print(f"{t['cmd_hash'][:12]}  {t.get('protocol')}  x{t.get('cluster_size')}  "
              f"{str(t['commands']).splitlines()[0][:60]}")
