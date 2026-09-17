"""서버 없이 PC 에서 센서 설정을 검사한다.  python sensor/check_config.py

userdb 해석 규칙은 cowrie src/cowrie/core/auth.py (UserDB.load / checklogin) 를 따라 했다.
"""

import configparser
import re
import sys
from pathlib import Path

ETC = Path(__file__).parent / "etc"

# 발표 슬라이드에 올릴 조합들. 기대값이 바뀌면 여기와 userdb.txt 를 같이 고친다
EXPECT = [
    ("root", "root", False),
    ("root", "123456", True),
    ("root", "vizxv", True),
    ("root", "wrongpass", False),
    ("admin", "anything", True),
    ("ubnt", "ubnt", True),
    ("guest", "guest", False),
]


def parse_rule(s: str):
    m = re.match(r"^/(.+)/(i)?$", s)
    if m:
        return re.compile(m.group(1), re.IGNORECASE if m.group(2) else 0)
    return s


def match(rule, value: str) -> bool:
    if isinstance(rule, re.Pattern):
        return rule.search(value) is not None
    return rule == "*" or rule == value


def load_userdb(path: Path) -> tuple[list[tuple[object, object, bool, int]], list[str]]:
    errors = []
    raw = path.read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as e:
        return [], [f"{path.name}: ASCII 아닌 문자 (byte {e.start}). cowrie 가 로드에 실패함"]

    rules = []
    for no, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 3:
            errors.append(f"{path.name}:{no}: 필드가 3개가 아님 -> {line!r}")
            continue
        user, passwd = parts[0], parts[2]
        if "#" in passwd or passwd != passwd.strip():
            errors.append(f"{path.name}:{no}: 비밀번호에 공백/# 이 섞임 (인라인 주석?) -> {passwd!r}")
        allow = not passwd.startswith("!")
        passwd = passwd.lstrip("!")
        rules.append((parse_rule(user), parse_rule(passwd), allow, no))
    return rules, errors


def check_login(rules, user: str, passwd: str) -> tuple[bool, int | None]:
    for u, p, allow, no in rules:
        if match(u, user) and match(p, passwd):
            return allow, no
    return False, None


def shadowed(rules) -> list[str]:
    out = []
    for i, (u, p, _, no) in enumerate(rules):
        if isinstance(u, re.Pattern) or isinstance(p, re.Pattern):
            continue
        for u0, p0, _, no0 in rules[:i]:
            if isinstance(u0, re.Pattern) or isinstance(p0, re.Pattern):
                continue
            if u0 in ("*", u) and p0 in ("*", p):
                out.append(f"userdb.txt:{no}: {no0}번 줄에 가려져 절대 매칭되지 않음")
                break
    return out


def check_cfg(path: Path) -> list[str]:
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(path, encoding="utf-8")
    errors = []
    if cfg.get("honeypot", "hostname", fallback="svr04") == "svr04":
        errors.append("cowrie.cfg: hostname 이 기본값 svr04")
    if cfg.get("telnet", "enabled", fallback="false").lower() not in ("true", "yes", "1"):
        errors.append("cowrie.cfg: [telnet] enabled 가 꺼져 있음")
    version = cfg.get("ssh", "version", fallback="")
    if not version.startswith(("SSH-2.0-", "SSH-1.99-")):
        errors.append(f"cowrie.cfg: [ssh] version 형식 오류 -> {version!r}")
    return errors


def main() -> int:
    rules, errors = load_userdb(ETC / "userdb.txt")
    errors += check_cfg(ETC / "cowrie.cfg")
    warnings = shadowed(rules)

    for user, passwd, want in EXPECT if rules else []:
        got, no = check_login(rules, user, passwd)
        mark = "ok " if got == want else "BAD"
        print(f"  [{mark}] {user}/{passwd:<10} -> {'허용' if got else '거부'} (line {no})")
        if got != want:
            errors.append(f"{user}/{passwd}: 기대 {want}, 실제 {got}")

    for w in warnings:
        print(f"  warn: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    print("통과" if not errors else f"실패 {len(errors)}건")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
