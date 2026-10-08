"""cmd_hash 생성 모듈 (팀 가이드 [정해진 것] 2번 규칙 준수)

규칙:
1. 그 세션의 명령(command.input, command.failed)을 시간 순서대로 정렬
2. 줄마다 앞뒤 공백을 지우고, 공백 여러 개는 하나로
3. IP 주소는 IP, http:// https:// ftp:// 로 시작하는 주소는 URL 이라는 글자로 바꾸기
4. 줄바꿈(\n)으로 이어 붙여서 sha256 -> 16진수 소문자 64자
5. 명령이 없는 세션은 None 반환
"""

import hashlib
import re

# IP 주소 정규식 (IPv4)
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

# URL 정규식 (http://, https://, ftp://)
URL_PATTERN = re.compile(r'\b(?:https?|ftp)://[^\s]+', re.IGNORECASE)


def normalize_command(cmd: str) -> str:
    """단일 명령어 문자열 정규화 (공백/IP/URL 치환)"""
    if not cmd:
        return ""
    # 1. 앞뒤 공백 제거 및 연속 공백 1개로 축소
    cmd = re.sub(r'\s+', ' ', cmd.strip())
    # 2. URL 치환 (URL)
    cmd = URL_PATTERN.sub('URL', cmd)
    # 3. IP 치환 (IP)
    cmd = IP_PATTERN.sub('IP', cmd)
    return cmd


def compute_cmd_hash(commands: list[str]) -> str | None:
    """세션의 명령어 리스트를 받아 sha256 64자 소문자 cmd_hash 생성"""
    normalized_lines = [normalize_command(c) for c in commands if c and c.strip()]
    
    # 명령어가 없는 세션은 None (DB에 NULL로 들어감)
    if not normalized_lines:
        return None
    
    # 줄바꿈(\n)으로 이어붙이기
    joined_text = "\n".join(normalized_lines)
    
    # sha256 16진수 소문자 64자 생성
    return hashlib.sha256(joined_text.encode('utf-8')).hexdigest().lower()
