"""Quick check of the agentic RAG agent.  Run from the backend folder:  python check_rag.py

Uses a few built-in sample documents (not your database), so it only tests the key, the packages
and the LangGraph flow.
"""
from app import rag_agent

DOCS = [
    {"id": 1, "title": "Vacation policy", "keywords": "conge conges holiday annual leave",
     "content": "Every employee gets 22 paid vacation days per year.\nRequests need manager approval at least 7 days ahead."},
    {"id": 2, "title": "Sick leave", "keywords": "maladie arret medical certificate",
     "content": "A medical certificate is required after 2 consecutive days of sickness.\nSend it to HR within 48 hours."},
]

if not rag_agent.available():
    raise SystemExit(f"RAG agent unavailable: {rag_agent.last_error or 'set GEMINI_API_KEY in backend/.env'}")

for q in ("How many vacation days do I get?", "Do I need a doctor's note when I am sick?", "What is the dress code on Mars?"):
    res = rag_agent.run(q, DOCS)
    print(f"\nQ: {q}")
    print("   ", res if res else f"FAILED: {rag_agent.last_error}")
