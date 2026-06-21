# Learning the Claude API — a 4-rung ladder

Each script adds **one** concept on top of the last, in the same
`INPUT → THINK → ACT` shape. Run them in order.

| Rung | File | Concept | Run it |
|---|---|---|---|
| 1 | `summarize.py` | one-shot request/response | `python summarize.py` then paste, Ctrl-D |
| 2 | `02_stream.py` | streaming (tokens appear live) | `python 02_stream.py` then paste, Ctrl-D |
| 3 | `03_extract.py` | structured outputs (validated JSON) | `python 03_extract.py` then paste, Ctrl-D |
| 4 | `04_agent.py` | tool use (Claude calls your code) | `python 04_agent.py "what is 23*17+100?"` |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # anthropic, python-dotenv, pydantic
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # your key from console.anthropic.com
python 03_extract.py
```

Your API key lives in `.env` (gitignored, never committed). Each script calls
`load_dotenv()` to read it, so you don't export anything.

If the key is ever exposed (e.g. pasted into a chat), rotate it at
console.anthropic.com: create a new key, replace the value in `.env`, revoke the old one.

## The mental model

- **Rung 1–2** = Claude *talks*. Same call, two ways to read the reply.
- **Rung 3** = the answer becomes *data* your code can use → this is the bridge to automation.
- **Rung 4** = Claude *acts* by calling functions you wrote → this is what makes an "agent".

All four use `claude-opus-4-8` (swap to `claude-haiku-4-5` for cheaper/faster
while practising). Models, params, and patterns: run `/claude-api` anytime.
