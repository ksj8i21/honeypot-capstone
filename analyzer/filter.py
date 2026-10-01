from typing import List, Dict, Any
from supabase import Client


def fetch_ai_targets(sb: Client, max_rows: int = 1000) -> List[Dict[Any, Any]]:
    """
    Supabase SQL 함수(pick_ai_targets)를 RPC로 호출하여 AI 분석 대상 세션을 선별합니다.

    :param sb: Supabase Client 객체
    :param max_rows: 하루 처리 상한 개수 (기본값 1000)
    :return: 분석 대상 세션 정보 리스트
             [{'cmd_hash': ..., 'protocol': ..., 'sensor_id': ..., 'session_id': ..., 'commands': ..., 'cluster_size': ...}, ...]
    """
    try:
        # Supabase RPC 호출
        response = sb.rpc("pick_ai_targets", {"max_rows": max_rows}).execute()
        rows = response.data or []

        # 데이터 검증 및 필터링 (commands가 비어있거나 필수 값이 누락된 행 제외)
        valid_rows = []
        for row in rows:
            cmd_hash = row.get("cmd_hash")
            commands = row.get("commands")

            if not cmd_hash or not commands or not commands.strip():
                continue

            valid_rows.append(row)

        print(f"[filter.py] pick_ai_targets 호출 완료: 총 {len(valid_rows)}건의 유효 대상 선별됨.")
        return valid_rows

    except Exception as e:
        print(f"[filter.py] 분석 대상 조회 중 오류 발생: {e}")
        raise e


if __name__ == "__main__":
    # 독립 실행 테스트용 예시
    import os
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")

    if url and key:
        supabase = create_client(url, key)
        targets = fetch_ai_targets(supabase, max_rows=10)
        print(f"테스트 결과 ({len(targets)}건):")
        for t in targets:
            print(f"- [Hash: {t['cmd_hash'][:8]}...] Protocol: {t['protocol']}, Cluster Size: {t['cluster_size']}")
    else:
        print("환경 변수(SUPABASE_URL, SUPABASE_SECRET_KEY)가 설정되지 않아 독립 테스트를 건너띕니다.")
