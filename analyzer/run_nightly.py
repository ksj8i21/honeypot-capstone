import json
import os
from pathlib import Path
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from supabase import create_client, Client

# 상수 및 설정 정의
BATCH_ID_FILE = Path("data/ai_batch_id.txt")
MAX_ROWS = 1000
CHUNK_SIZE = 500
MODEL_NAME = "claude-haiku-4-5"

INTENTS = ["코인채굴", "봇넷가담", "정찰", "자격증명탈취", "랜섬웨어", "기타"]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["intent", "severity", "summary", "ttp"],
    "properties": {
        "intent": {"type": "string", "enum": INTENTS},
        "severity": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "summary": {"type": "string"},
        "ttp": {"type": "array", "items": {"type": "string"}},
    },
}


def get_supabase_client() -> Client:
    """Supabase 클라이언트 생성 (.env 환경변수 이용)"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL 또는 SUPABASE_SECRET_KEY가 설정되지 않았습니다.")
    return create_client(url, key)


def load_prompt() -> str:
    """시스템 프롬프트 파일을 읽어옵니다."""
    prompt_path = Path("analyzer/prompts/session_intent.md")
    if not prompt_path.exists():
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def chunk_list(lst, size):
    """리스트를 지정한 크기로 나눕니다."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def process_existing_batch(client: anthropic.Anthropic, sb: Client) -> bool:
    """
    이전에 제출한 Batch가 있는지 확인하고 처리합니다.
    - 처리 완료 시: DB 저장 후 batch_id 파일 삭제 -> True 반환 (새 요청 진행 가능)
    - 진행 중인 경우: 처리 중단 -> False 반환 (새 요청 제출 중단)
    - 저장할 batch가 없거나 성공적으로 회수된 경우: True 반환
    """
    if not BATCH_ID_FILE.exists():
        return True

    batch_id = BATCH_ID_FILE.read_text(encoding="utf-8").strip()
    if not batch_id:
        return True

    print(f"[+] 이전 Batch 상태 확인 중... (Batch ID: {batch_id})")
    batch = client.messages.batches.retrieve(batch_id)

    if batch.processing_status != "ended":
        print(f"[-] 이전 Batch가 아직 진행 중입니다 (상태: {batch.processing_status}). 오늘은 새로 보내지 않고 종료합니다.")
        return False

    print("[+] Batch 처리가 완료되었습니다. 결과를 회수하여 DB에 저장합니다.")
    rows_to_insert = []

    for r in client.messages.batches.results(batch_id):
        # errored, expired 등 성공하지 않은 건은 건너뜀 (다음 날 pick_ai_targets에서 자동 재선별됨)
        if r.result.type != "succeeded":
            continue

        msg = r.result.message
        text = next(b.text for b in msg.content if b.type == "text")
        out = json.loads(text)

        rows_to_insert.append({
            "cmd_hash": r.custom_id,
            "intent": out["intent"],
            "severity": out["severity"],
            "summary": out["summary"],
            "ttp": out["ttp"],
            "model": msg.model,
            "tokens_in": msg.usage.input_tokens,
            "tokens_out": msg.usage.output_tokens,
        })

    # 결과 DB Upsert (CHUNK_SIZE 단위)
    if rows_to_insert:
        print(f"[+] 총 {len(rows_to_insert)}건의 결과를 ai_analysis 테이블에 저장합니다.")
        for chunk in chunk_list(rows_to_insert, CHUNK_SIZE):
            sb.table("ai_analysis").upsert(
                chunk, on_conflict="cmd_hash", ignore_duplicates=True
            ).execute()
        print("[+] DB 저장 완료.")

    # 회수 및 저장 완료 후 Batch ID 파일 삭제
    BATCH_ID_FILE.unlink(missing_ok=True)
    print("[+] 이전 Batch 작업이 정상 완료되어 Batch ID 파일을 삭제했습니다.")
    return True


def submit_new_batch(client: anthropic.Anthropic, sb: Client):
    """분석 대상을 조회하여 새 Batch 작업을 생성 및 제출합니다."""
    print("[+] 새 분석 대상 조회를 시작합니다...")
    res = sb.rpc("pick_ai_targets", {"max_rows": MAX_ROWS}).execute()
    rows = res.data or []

    if not rows:
        print("[+] 분석할 신규 대상이 없습니다. 작업을 종료합니다.")
        return

    print(f"[+] 총 {len(rows)}건의 분석 대상을 찾았습니다. Batch 요청을 생성합니다.")

    prompt_text = load_prompt()
    system_prompt = [
        {
            "type": "text",
            "text": prompt_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    requests = [
        Request(
            custom_id=row["cmd_hash"],
            params=MessageCreateParamsNonStreaming(
                model=MODEL_NAME,
                max_tokens=1024,
                system=system_prompt,
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[
                    {
                        "role": "user",
                        "content": f"protocol: {row['protocol']}\ncommands:\n{row['commands']}",
                    }
                ],
            ),
        )
        for row in rows
    ]

    print("[+] Anthropic Batch API 제출 중...")
    batch = client.messages.batches.create(requests=requests)

    # batch_id 저장
    BATCH_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    BATCH_ID_FILE.write_text(batch.id, encoding="utf-8")
    print(f"[+] 새 Batch가 정상적으로 제출되었습니다. (Batch ID: {batch.id})")


def main():
    anthropic_client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    supabase_client = get_supabase_client()

    # 1단계: 이전 Batch 회수 및 완료 여부 검사
    can_proceed = process_existing_batch(anthropic_client, supabase_client)
    if not can_proceed:
        return

    # 2~5단계: 새 분석 대상 선별 및 Batch 제출
    submit_new_batch(anthropic_client, supabase_client)


if __name__ == "__main__":
    main()