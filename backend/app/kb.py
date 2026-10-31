"""Tiny offline retrieval + intent detection for the HR assistant (standard library only).

Answers come from the company documents the admin maintains (KnowledgeDoc). Retrieval is keyword
based with accent folding and light stemming, and each document can carry extra keywords
(French / darija / synonyms) so "congé" finds the vacation policy. An LLM can phrase the answer
later (see llm.py) but is never the source of the facts.
"""
import re
import unicodedata

STOP = set(
    "the and for are you your with that this what when where which who how can could should would will "
    "does did have has had not but from about into than then them they their our out any all get got "
    "des les une est pas pour que qui sur dans avec par aux mon ton son nos vos ses mes tes ces cet cette "
    "quel quelle quels combien comment est-ce".split()
)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _stem(w: str) -> str:
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
        return w[:-1]
    return w


def tokens(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", norm(text)) if len(w) > 2 and w not in STOP}


def _chunks(content: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n", content) if p.strip()]
    return parts or [content.strip()]


def search(question: str, docs: list[dict], k: int = 2, threshold: float = 1.5) -> list[dict]:
    """docs: [{id, title, keywords, content}] -> best matching passages, best first."""
    q = tokens(question)
    if not q:
        return []
    hits = []
    for d in docs:
        meta = tokens(d["title"] + " " + d.get("keywords", ""))
        bonus = 1.5 * len(q & meta)
        for chunk in _chunks(d["content"]):
            score = len(q & tokens(chunk)) + bonus
            if score >= threshold:
                hits.append({"doc_id": d["id"], "title": d["title"], "text": chunk, "score": round(score, 2)})
    hits.sort(key=lambda h: h["score"], reverse=True)
    seen, out = set(), []
    for h in hits:
        if h["text"] in seen:
            continue
        seen.add(h["text"])
        out.append(h)
        if len(out) == k:
            break
    return out


# ---------------------------------------------------------------- intents
DOC_PATTERNS = {
    "salary_certificate": r"attestation de salaire|salary (certificate|statement|slip)|proof of (income|salary)|attestation de revenu|certificat de salaire",
    "leave_summary": r"releve de conges?|leave (summary|statement|certificate|record)|attestation de conges?|solde de conges? (document|attestation)",
    "training_record": r"training (certificate|record|attestation|history)|attestation de formation|certificat de formation|releve de formation",
    "work_certificate": r"attestation de travail|attestation de presence|work certificate|employment (certificate|letter|proof)|certificate of employment|proof of employment|attestation (d'?)?emploi|attestation travail",
}
REQUEST_WORDS = (
    r"\b(need|want|request|get|give|issue|generate|send|prepare|download|obtain|can i have|could i have|"
    r"demande|besoin|veux|voudrais|souhaite|obtenir|delivrer|nheb|n7eb|nhebb|nest7a9|ne7tej|nehtej|7ab|3tini|a3tini|jibli)\b"
)


def detect_intent(question: str) -> tuple[str, dict]:
    n = norm(question)
    if re.search(REQUEST_WORDS, n):
        for doc_type, pattern in DOC_PATTERNS.items():
            if re.search(pattern, n):
                return "document_request", {"doc_type": doc_type}
    asks_count = re.search(r"\b(balance|how many|how much|left|remaining|reste|solde|combien|kadech|9adeech|kaddech|chhal)\b", n)
    if asks_count and re.search(r"\b(leave|vacation|holiday|days off|conges?|jours?|3utla|3otla)\b", n):
        return "leave_balance", {}
    if re.search(r"\b(my|mes|mon|mte3i|mt3i)\b", n) and re.search(r"\b(training|trainings|formation|formations|course|courses)\b", n):
        return "training_status", {}
    if asks_count and re.search(r"\b(training|trainings|formation|formations)\b", n) and re.search(r"\b(done|completed|did|fait|faites|faite|suivi|suivies|3malt|3amalt|amelt)\b", n):
        return "training_status", {}
    return "knowledge", {}
