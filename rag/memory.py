# memory.py — beyond the ladder: an agent that REMEMBERS across restarts.
#
# The 4-rung ladder's memory was the `messages` list in assistant.py — it dies on
# /reset and can't outgrow the context window. This is the OTHER kind of memory:
# EXTERNAL memory, a.k.a. RAG. The whole thing is three moves, nothing more:
#
#   EMBED     text → a vector (a list of numbers that encodes *meaning*, not words)
#   STORE     keep the vectors on disk, so they survive a restart
#   RECALL    embed the question, pull back the nearest memories, paste them in
#
#   python memory.py --seed     # write a few starter facts into the store
#   python memory.py            # chat; it recalls relevant facts before answering
#
# Generation is still Claude (the ladder's engine). Only the EMBED step uses a small
# LOCAL model — sentence-transformers — because Anthropic has no embeddings endpoint,
# and local means it runs offline and costs nothing per query.
#
# Needs two extra packages beyond the ladder:  pip install sentence-transformers numpy

import os
import sys
import json
from dotenv import load_dotenv
import numpy as np
import anthropic

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-opus-4-8"     # swap to claude-haiku-4-5 for cheaper/faster practice

# The store lives next to this file, so it's found no matter where you run from.
STORE_PATH = os.path.join(os.path.dirname(__file__), "memory_store.json")

R, B, D = "\033[0m", "\033[1m", "\033[2m"
CY, GRN = "\033[36m", "\033[32m"


# ── THE EMBEDDER ──────────────────────────────────────────────────────────────
# Loaded lazily: the model is ~90MB and downloads on first use, so we don't pay
# that cost just to print a banner. encode() returns a 384-number vector; we
# normalize it to length 1 so that a dot product IS cosine similarity later.
_model = None


def embed(text: str) -> np.ndarray:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"{D}  (loading embedding model — first run downloads ~90MB){R}", flush=True)
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    v = np.asarray(_model.encode(text), dtype="float32")
    return v / (np.linalg.norm(v) + 1e-9)


# ── THE STORE ─────────────────────────────────────────────────────────────────
# The "simple vector store" from the project brief: a list of (text, vector) pairs
# saved as JSON. A real system uses Chroma / FAISS / sqlite-vec; the IDEA is this.
class VectorMemory:
    def __init__(self, path: str = STORE_PATH):
        self.path = path
        self.items = []   # each: {"text": str, "vec": np.ndarray}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for r in json.load(f):
                    self.items.append({"text": r["text"], "vec": np.asarray(r["vec"], "float32")})

    def add(self, text: str):
        self.items.append({"text": text, "vec": embed(text)})
        self._save()

    def recall(self, query: str, k: int = 3):
        """Embed the question, return the k nearest memories as (text, score)."""
        if not self.items:
            return []
        q = embed(query)
        mat = np.vstack([it["vec"] for it in self.items])   # (n, 384)
        scores = mat @ q                                     # cosine — all are unit length
        idx = np.argsort(-scores)[:k]
        return [(self.items[i]["text"], float(scores[i])) for i in idx]

    def _save(self):
        raw = [{"text": it["text"], "vec": it["vec"].tolist()} for it in self.items]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(raw, f)


# ── GENERATION ────────────────────────────────────────────────────────────────
# RAG in one function: recall the relevant memories, paste them into the prompt as
# context, let Claude answer. Retrieval is the INPUT side of structured output —
# Module 2 got the right data *out*; this gets the right context *in*.
SYSTEM = (
    "You are a helpful assistant with a long-term memory. Use the RECALLED MEMORIES "
    "below when they're relevant to the user's message. If they don't help, just "
    "answer normally and don't mention them or the fact that you have a memory."
)


def answer(mem: VectorMemory, user: str):
    hits = mem.recall(user)
    if hits:   # show what was retrieved, so the lesson is visible while you chat
        print(f"{D}  recalled:{R}")
        for text, score in hits:
            print(f"{D}    {score:.2f}  {text}{R}")
    context = "\n".join(f"- {t}" for t, _ in hits) or "(no memories yet)"
    prompt = f"RECALLED MEMORIES:\n{context}\n\nUser: {user}"

    # The model call can fail mid-stream on a transient server hiccup (HTTP 5xx).
    # That's Anthropic's side, not ours — so retry once, and if it still fails,
    # print a note and return to the prompt instead of crashing the whole REPL.
    print(f"{CY}assistant ›{R} ", end="", flush=True)
    for attempt in (1, 2):
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=1000,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    print(chunk, end="", flush=True)
            print("\n")
            return
        except anthropic.APIStatusError as e:
            if attempt == 1:   # transient? try one more time before giving up
                continue
            print(f"\n{D}  (API error {e.status_code} — try asking again){R}\n")


# ── STARTER FACTS ─────────────────────────────────────────────────────────────
# Seeded so retrieval is demonstrable: ask "how long do I have to send something
# back?" and it recalls the refund fact — with ZERO shared words. That's the whole
# point of embeddings: nearness in MEANING, not in spelling.
SEEDS = [
    "The user prefers short, technical answers and dislikes corporate filler.",
    "The user is learning to build AI agents directly from the raw Claude API, no framework.",
    "The demo shop's refund policy is 30 days, no questions asked.",
    "Orders over $200 ship for free; everything else is a flat $7.",
    "The support team escalates to a human whenever a customer threatens to cancel.",
]


def seed():
    mem = VectorMemory()
    print(f"Seeding {len(SEEDS)} facts → {os.path.basename(STORE_PATH)}\n")
    for fact in SEEDS:
        mem.add(fact)
        print(f"  remembered: {fact}")
    print(f"\nNow run:  python memory.py")


# ── THE REPL ──────────────────────────────────────────────────────────────────
def main():
    mem = VectorMemory()
    print(f"\n  {B}memory{R}  {D}· RAG: embed · store · recall · {len(mem.items)} memories on disk{R}")
    print(f"  {D}/remember <text>  store a fact     /exit  quit{R}\n")
    while True:
        try:
            user = input(f"{B}you ›{R} ").strip()
        except EOFError:
            print()
            break
        if not user:
            continue
        if user in ("/exit", "/quit"):
            break
        if user.startswith("/remember "):
            fact = user[len("/remember "):].strip()
            mem.add(fact)
            print(f"{GRN}  remembered.{R} {D}({len(mem.items)} total){R}\n")
            continue
        answer(mem, user)


if __name__ == "__main__":
    if "--seed" in sys.argv:
        seed()
    else:
        main()
