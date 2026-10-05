import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from supabase import Client

# 기본 설정 및 모델 정의
MODEL_NAME = "claude-haiku-4-5"
PROMPT_PATH = Path("analyzer/prompts/session_intent.md")
CHUNK_SIZE = 500

# DB CHECK 제약과 일치하는 6가지 intent 목록
INTENTS = ["코인채굴", "봇넷가담", "정찰", "자격증명탈취", "랜섬웨어", "기타"]

# Structured Outputs를 위한 JSON Schema
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


def load_prompt() -> str:
    """시스템 프롬프트 파일(session_intent.md)을 읽어옵니다."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"시스템 프롬프트 파일을 찾을 수 없습니다: {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def chunk_list(lst: List[Any], size: int):
    """리스트를 지정한 크기(CHUNK_SIZE) 단위로 분할합니다."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def create_and_submit_batch(
    client: anthropic.Anthropic, rows: List[Dict[str, Any]]
) -> Optional[str]:
    """
    선별된 세션 목록을 받아서 Anthropic Batch API에 제출하고 batch_id를 반환합니다.
    """
    if not rows:
        print("[classify.py] 제출할 분석 대상이 없습니다.")
        return None

    prompt_text = load_prompt()

    # Ephemeral Cache Control 설정 (4,096 토큰 이상 시 프롬프트 캐싱 적용)
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
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": SCHEMA,
                    }
                },
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

    print(f"[classify.py] 총 {len(requests)}건의 요청을 Anthropic Batch API에 제출합니다...")
    batch = client.messages.batches.create(requests=requests)
    print(f"[classify.py] Batch 생성 완료 (Batch ID: {batch.id})")

    return batch.id


def fetch_and_save_batch_results(
    client: anthropic.Anthropic, sb: Client, batch_id: str
) -> bool:
    """
    제출된 Batch ID의 상태를 확인하고, 완료 시 결과를 회수하여 Supabase ai_analysis 테이블에 저장합니다.

    - 처리 완료 및 DB 저장 성공 시: True 반환
    - 아직 진행 중인 경우: False 반환
    """
    print(f"[classify.py] Batch 상태 확인 중... (Batch ID: {batch_id})")
    batch = client.messages.batches.retrieve(batch_id)

    if batch.processing_status != "ended":
        print(
            f"[classify.py] Batch가 아직 처리 중입니다. (현재 상태: {batch.processing_status})"
        )
        return False

    print("[classify.py] Batch 작업이 완료되었습니다. 결과를 회수합니다.")
    rows_to_upsert = []

    for r in client.messages.batches.results(batch_id):
        # 성공(succeeded)하지 않은 항목(errored, expired 등)은 건너뜀
        # DB에 저장되지 않으므로 다음 날 pick_ai_targets에서 자동으로 다시 추출됨
        if r.result.type != "succeeded":
            continue

        msg = r.result.message
        text = next(b.text for b in msg.content if b.type == "text")
        out = json.loads(text)

        rows_to_upsert.append({
            "cmd_hash": r.custom_id,
            "intent": out["intent"],
            "severity": out["severity"],
            "summary": out["summary"],
            "ttp": out["ttp"],
            "model": msg.model,
            "tokens_in": msg.usage.input_tokens,
            "tokens_out": msg.usage.output_tokens,
        })

    if rows_to_upsert:
        print(f"[classify.py] 총 {len(rows_to_upsert)}건의 분석 결과를 ai_analysis 테이블에 저장합니다.")
        # 500개 단위 Chunking Upsert
        for chunk in chunk_list(rows_to_upsert, CHUNK_SIZE):
            sb.table("ai_analysis").upsert(
                chunk, on_conflict="cmd_hash", ignore_duplicates=True
            ).execute()
        print("[classify.py] ai_analysis 테이블 저장 완료.")
    else:
        print("[classify.py] 회수하여 저장할 성공(succeeded) 결과가 없습니다.")

    return True