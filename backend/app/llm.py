"""Optional LLM access using only the standard library.

Two providers are supported, picked from the environment (see backend/.env.example):

* Google Gemini  - set GEMINI_API_KEY (or GOOGLE_API_KEY)
* Anthropic      - set ANTHROPIC_API_KEY

Without a key every caller falls back to the offline rule-based answer, so the app always works.
Callers must only send data the model needs (see pseudonymise in routers/analytics.py) and must
wrap untrusted text in tags.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from . import config  # noqa: F401  (loads backend/.env before the keys are read)

log = logging.getLogger("hrinone.llm")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Google "express mode" keys are served from this endpoint instead; it is tried as a fallback.
VERTEX_URL = "https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent"

last_error: str | None = None  # last failure, shown by `python check_llm.py` and in the server log


def _gemini_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def provider() -> str | None:
    if _gemini_key():
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def available() -> bool:
    return provider() is not None


def _post(url: str, headers: dict, body: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.load(res)


def _gemini(system: str, user: str, max_tokens: int, timeout: int) -> str | None:
    model = os.getenv("HRINONE_MODEL", "gemini-flash-latest")
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        # thinking tokens count against the limit on current Gemini models, so leave headroom
        "generationConfig": {"maxOutputTokens": max_tokens + 2048, "temperature": 0.3},
    }
    headers = {"content-type": "application/json", "x-goog-api-key": _gemini_key()}
    data, errors = None, []
    for template in (GEMINI_URL, VERTEX_URL):
        url = template.format(model=model)
        try:
            data = _post(url, headers, body, timeout)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            errors.append(f"{url.split('/')[2]} -> HTTP {e.code}: {detail}")
            if e.code not in (400, 401, 403, 404):
                break
    if data is None:
        raise RuntimeError(" | ".join(errors))
    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    return text or None


def _anthropic(system: str, user: str, max_tokens: int, timeout: int) -> str | None:
    body = {
        "model": os.getenv("HRINONE_MODEL", "claude-sonnet-4-6"),
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {"content-type": "application/json", "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
               "anthropic-version": "2023-06-01"}
    data = _post(ANTHROPIC_URL, headers, body, timeout)
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    return text or None


def complete(system: str, user: str, max_tokens: int = 500, timeout: int = 25) -> str | None:
    global last_error
    kind = provider()
    if not kind:
        return None
    try:
        text = (_gemini if kind == "gemini" else _anthropic)(system, user, max_tokens, timeout)
        last_error = None if text else "The model returned an empty answer"
        return text
    except Exception as e:  # never break the feature because the model is unreachable
        last_error = f"{type(e).__name__}: {e}"
        log.warning("LLM call failed (%s): %s", kind, last_error)
        return None
