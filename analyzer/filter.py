from typing import List, Dict, Any
from supabase import Client


def fetch_ai_targets(sb: Client, max_rows: int = 1000) -> List[Dict[str, Any]]:
    """
    Supabase RPC 함수(pick_ai_targets)를 호출하여 AI 분석 대상 세션을 선별합니다.

    :param sb: Supabase Client 객체
    :param max_rows: 하루 처리 상한 개수 (기본값: 1000)
    :return: 분석 대상 세션 정보 리스트
             [{'cmd_hash': ..., 'protocol': ..., 'sensor_id': ..., 'session_id': ..., 'commands': ..., 'cluster_size': ...}, ...]
    """
    try:
        # 가이드 4-1 명세에 맞추어 pick_ai_targets RPC 호출
        res = sb.rpc("pick_ai_targets", {"max_rows": max_rows}).execute()
        rows = res.data or []

        # 데이터 검증: cmd_hash와 commands가 유효한 데이터만 필터링
        valid_rows = []
        for row in rows:
            cmd_hash = row.get("cmd_hash")
            commands = row.get("commands")

            if not cmd_hash or not commands or not str(commands).strip():
                continue

            valid_rows.append(row)

        print(f"[+] [filter.py] pick_ai_targets 조회 완료: 총 {len(valid_rows)}건의 분석 대상을 선별했습니다.")
        return valid_rows

    except Exception as e:
        print(f"[-] [filter.py] 분석 대상 조회 중 오류가 발생했습니다: {e}")
        raise e


if __name__ == "__main__":
    import os
    from supabase import create_client

    # 단독 테스트 실행 로직
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")

    if not url or not key:
        print("[-] SUPABASE_URL 또는 SUPABASE_SECRET_KEY 환경 변수가 설정되지 않아 테스트를 종료합니다.")
    else:
        sb_client = create_client(url, key)
        targets = fetch_ai_targets(sb_client, max_rows=10)
        print(f"\n[+] 테스트 조회 결과 ({len(targets)}건):")
        for t in targets:
            print(f" - [Hash: {t.get('cmd_hash', '')[:8]}...] Protocol: {t.get('protocol')}, Cluster Size: {t.get('cluster_size')}")