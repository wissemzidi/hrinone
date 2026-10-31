"""Tiny .env loader (standard library only).

Reads backend/.env once at import time and puts each KEY=VALUE into os.environ unless the
variable is already set in the real environment. Secrets such as the LLM key therefore live in
a file that git ignores, never in the source code and never in the frontend.
"""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load(path: Path = ENV_FILE) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load()
