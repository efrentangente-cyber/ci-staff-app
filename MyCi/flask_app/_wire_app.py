"""Restore app.py from transcript + offline wiring. Run: python _wire_app.py"""
import json
import re
from pathlib import Path

TRANSCRIPT = Path(
    r"C:\Users\carba\.cursor\projects\c-Users-carba-AndroidStudioProjects-MyCi\agent-transcripts"
    r"\8a5964d5-6703-475a-be6f-be379165851c\8a5964d5-6703-475a-be6f-be379165851c.jsonl"
)
OUT = Path(__file__).resolve().parent / "app.py"


def main() -> None:
    best, bestlen = None, 0
    for line in TRANSCRIPT.open(encoding="utf-8"):
        if "from flask import Flask" not in line or "init_db" not in line or "user_query" not in line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = (obj.get("message") or {}).get("content")
        if not t or t[0].get("type") != "text":
            continue
        text = t[0].get("text", "")
        m = re.search(r"<user_query>\s*(.*)\s*</user_query>", text, re.DOTALL)
        if not m:
            continue
        body = m.group(1).strip()
        if len(body) > bestlen and "def init_db" in body:
            best, bestlen = body, len(body)
    if not best:
        raise SystemExit("No embedded app in transcript — paste your full app.py into the project first")
    s = best
    s = s.replace(
        "import resend\n",
        "import resend\nfrom offline_interview_api import offline_interview_bp, ensure_offline_migrations\n",
        1,
    )
    s = s.replace("DATABASE = 'app.db'\n", "DATABASE = 'app.db'\napp.config['DATABASE'] = DATABASE\n", 1)
    s = s.replace(
        "# Initialize database on startup\ninit_db()\n",
        "# Initialize database on startup\ninit_db()\n\n"
        "with app.app_context():\n    ensure_offline_migrations()\n"
        "app.register_blueprint(offline_interview_bp)\n",
        1,
    )
    OUT.write_text(s, encoding="utf-8")
    print("OK wrote", OUT, "bytes", len(s))


if __name__ == "__main__":
    main()
