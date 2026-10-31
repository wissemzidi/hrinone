"""Quick check of the AI key.  Run from the backend folder:  python check_llm.py"""
from app import llm

if not llm.available():
    raise SystemExit("No key found. Put GEMINI_API_KEY=... in backend/.env")

print("Provider:", llm.provider())
answer = llm.complete("Answer in one short sentence.", "Say that the HR assistant is connected.", max_tokens=40)
if answer:
    print("OK:", answer)
else:
    print("FAILED:", llm.last_error)
