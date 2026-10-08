"""매일 03:00 실행 (deploy/honeypot-analyzer.timer). 이름 바꾸지 말 것.

    python -m analyzer.run_nightly
    python -m analyzer.run_nightly --max-rows 3      # 테스트: 2~3건만 제출
    python -m analyzer.run_nightly --dry-run         # 대상만 출력, 제출 안 함

① 어제 batch 회수 (안 끝났으면 오늘은 제출 안 하고 종료)
② 대상 고르기 → ③ 0건이면 종료 → ④ batch 제출 → ⑤ batch id 저장
"""

import argparse
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from supabase import create_client

from analyzer.classify import collect_batch, submit_batch
from analyzer.filter import pick_targets

MAX_ROWS = 150  # 하루 상한. 공격이 폭증해도 호출량이 같이 늘지 않게

# 저장소 루트 data/ (서버에서는 /opt/honeypot/data/). .gitignore 대상
BATCH_ID_FILE = Path(__file__).resolve().parent.parent / "data" / "ai_batch_id.txt"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AI 위협분석 야간 배치")
    ap.add_argument("--max-rows", type=int, default=MAX_ROWS)
    ap.add_argument("--dry-run", action="store_true", help="대상만 출력하고 batch 는 제출하지 않음")
    args = ap.parse_args(argv)

    load_dotenv()  # 서버는 systemd EnvironmentFile 로 이미 들어옴. 로컬 테스트용
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY

    # ① 어제 제출한 batch 회수
    if BATCH_ID_FILE.exists():
        batch_id = BATCH_ID_FILE.read_text(encoding="utf-8").strip()
        if batch_id:
            try:
                if not collect_batch(client, sb, batch_id):
                    print("[run] 이전 batch 가 안 끝나서 오늘은 새로 보내지 않음")
                    return 0
            except anthropic.NotFoundError:
                # 결과 보관 기간(29일)이 지났거나 잘못된 id. 저장 못 한 대상은 ② 에서 다시 뽑힘
                print(f"[run] batch {batch_id} 를 찾을 수 없음. id 파일만 정리")
        BATCH_ID_FILE.unlink(missing_ok=True)

    # ② 대상 고르기
    rows = pick_targets(sb, args.max_rows)

    # ③
    if not rows:
        print("[run] 새 분석 대상 없음")
        return 0
    if args.dry_run:
        for r in rows:
            print(f"  {r['cmd_hash'][:12]}  {r.get('protocol')}  x{r.get('cluster_size')}")
        return 0

    # ④ 제출 → ⑤ id 저장
    batch_id = submit_batch(client, rows)
    BATCH_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    BATCH_ID_FILE.write_text(batch_id, encoding="utf-8")
    print(f"[run] batch id 저장: {BATCH_ID_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
