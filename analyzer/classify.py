"""Batch 요청 만들기 / 결과 회수해서 ai_analysis 에 저장 (작업가이드 4-3, 4-4)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from supabase import Client

MODEL_NAME = "claude-haiku-4-5"  # 예산안 기준
MAX_TOKENS = 1024
CHUNK_SIZE = 500
# 페이로드가 통째로 명령 칸에 들어오는 경우가 있어서 한 요청 입력을 제한 (비용 상한)
MAX_COMMAND_CHARS = 8000

# 실행 위치(cwd)와 상관없이 찾도록 이 파일 기준 경로
PROMPT_PATH = Path(__file__).parent / "prompts" / "session_intent.md"

# DB CHECK 제약과 같아야 함 (db/01_schema.sql)
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


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def chunks(items: list[dict], size: int = CHUNK_SIZE) -> Iterator[list[dict]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def build_user_message(row: dict[str, Any]) -> str:
    commands = str(row["commands"])
    if len(commands) > MAX_COMMAND_CHARS:
        commands = commands[:MAX_COMMAND_CHARS] + "\n...(truncated)"
    # 공격자 입력을 태그로 감싸서 프롬프트 지시문과 구분 (프롬프트 0절)
    return f"protocol: {row.get('protocol') or 'unknown'}\n<commands>\n{commands}\n</commands>"


def build_requests(rows: list[dict[str, Any]]) -> list[Request]:
    # 모든 요청이 같은 system 을 써야 캐시가 공유됨. 날짜 등 바뀌는 값 넣지 말 것
    system = [{"type": "text", "text": load_prompt(), "cache_control": {"type": "ephemeral"}}]
    return [
        Request(
            custom_id=row["cmd_hash"],
            params=MessageCreateParamsNonStreaming(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                system=system,
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[{"role": "user", "content": build_user_message(row)}],
            ),
        )
        for row in rows
    ]


def submit_batch(client: anthropic.Anthropic, rows: list[dict[str, Any]]) -> str:
    batch = client.messages.batches.create(requests=build_requests(rows))
    print(f"[classify] batch 제출: {batch.id} ({len(rows)}건)")
    return batch.id


def parse_result(custom_id: str, msg) -> dict[str, Any] | None:
    """성공 응답 1건을 ai_analysis 행으로. 형식이 깨졌으면 None (다음 날 재분석됨)."""
    if msg.stop_reason != "end_turn":
        # max_tokens 로 잘렸거나 refusal 이면 JSON 이 불완전할 수 있음
        print(f"[classify] {custom_id}: stop_reason={msg.stop_reason}, 건너뜀")
        return None
    text = next((b.text for b in msg.content if b.type == "text"), "")
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        print(f"[classify] {custom_id}: JSON 파싱 실패, 건너뜀")
        return None
    if out.get("intent") not in INTENTS or out.get("severity") not in (1, 2, 3, 4, 5):
        print(f"[classify] {custom_id}: 스키마 밖 값 {out.get('intent')!r}/{out.get('severity')!r}, 건너뜀")
        return None
    return {
        "cmd_hash": custom_id,
        "intent": out["intent"],
        "severity": out["severity"],
        "summary": out.get("summary", ""),
        "ttp": [str(t) for t in out.get("ttp", [])],
        "model": msg.model,
        "tokens_in": msg.usage.input_tokens,
        "tokens_out": msg.usage.output_tokens,
    }


def collect_batch(client: anthropic.Anthropic, sb: Client, batch_id: str) -> bool:
    """batch 가 끝났으면 결과를 저장하고 True, 아직이면 False."""
    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        print(f"[classify] batch {batch_id} 진행 중 ({batch.processing_status})")
        return False

    rows: list[dict[str, Any]] = []
    failed = cache_read = cache_write = 0
    for r in client.messages.batches.results(batch_id):
        # errored / canceled / expired 는 저장 안 함 → ai_analysis 에 없으니 다음 날 다시 뽑힘
        if r.result.type != "succeeded":
            failed += 1
            continue
        msg = r.result.message
        cache_read += msg.usage.cache_read_input_tokens or 0
        cache_write += msg.usage.cache_creation_input_tokens or 0
        row = parse_result(r.custom_id, msg)
        if row is None:
            failed += 1
        else:
            rows.append(row)

    for chunk in chunks(rows):
        sb.table("ai_analysis").upsert(chunk, on_conflict="cmd_hash", ignore_duplicates=True).execute()

    print(f"[classify] batch {batch_id} 회수: 저장 {len(rows)}건, 실패/건너뜀 {failed}건")
    # 0 이면 프롬프트가 캐시 최소 길이(Haiku 4.5: 4,096 토큰)보다 짧거나 캐시가 안 먹은 것
    print(f"[classify] cache_read_input_tokens={cache_read}, cache_creation_input_tokens={cache_write}")
    return True
