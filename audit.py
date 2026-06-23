# audit.py — rung 6. The eval loop, pointed outward: score support transcripts.
#
# This is assistant.py's `extract` idea grown into a product. Instead of Claude
# answering YOU, a second Claude call JUDGES a support conversation against a rubric
# and hands back a typed verdict — the evaluator-optimizer pattern. It's the corner
# the platforms can't sell, because a vendor can't credibly grade its own homework.
#
#   python audit.py --generate   # write synthetic transcripts (with planted bugs)
#   python audit.py              # audit every transcript in transcripts/ → report
#
# The judge is just messages.parse() + a Pydantic schema (rung 3). Everything around
# it is reading files and rendering a page a support lead can scan in five seconds.

import os
import sys
import glob
from dotenv import load_dotenv
from pydantic import BaseModel
import anthropic

load_dotenv()
client = anthropic.Anthropic()

# Generating fake transcripts is trivial work — cheapest model is fine.
MODEL = "claude-haiku-4-5"
# The judge is the quality-sensitive half: a dumber judge gives worse verdicts, so
# keep it a notch up. It's also a DIFFERENT model than the generator, which is the
# point — it isn't grading its own homework. Push to opus when accuracy matters most.
JUDGE_MODEL = "claude-sonnet-4-6"

TRANSCRIPTS_DIR = "transcripts"


# ── THE RUBRIC ────────────────────────────────────────────────────────────────
# The five booleans ARE the product. A generic competitor scores "7/10". You score
# the dimensions a support lead actually loses sleep over — and `accurate` is the
# killer one: a hallucinated policy is a refund/legal liability, not a tone nitpick.
SEVERITIES = ["ok", "minor", "serious", "critical"]


class TranscriptAudit(BaseModel):
    resolved: bool            # did the customer's actual problem get solved?
    accurate: bool            # any invented policy / fact / false promise?
    appropriate_tone: bool    # professional — not curt, not robotic
    escalation_correct: bool  # escalated when it should, didn't when it shouldn't
    policy_compliant: bool    # followed the rules it was given
    severity: str             # one of SEVERITIES — how bad is the worst failure?
    evidence: str             # the exact quote that decides the verdict
    summary: str              # one line a manager reads


RUBRIC_PROMPT = """You are a meticulous quality auditor for customer-support conversations.
Read the transcript between a Customer and a support Agent, then judge the AGENT's
performance. Be strict — false reassurance is worse than an honest flag.

Score each dimension:
- resolved: did the customer's actual problem get solved (or correctly handed off)?
- accurate: is everything the agent stated true? Mark FALSE if the agent invented a
  policy, a number, a citation, or a promise it cannot back up.
- appropriate_tone: professional and human — not curt, dismissive, or robotic.
- escalation_correct: escalated to a human when it should, and didn't when it shouldn't.
- policy_compliant: followed the support rules (no leaking data, no unauthorized offers).

severity = the worst problem found: "ok" (clean), "minor", "serious", or "critical"
  (anything creating legal / financial / data risk — e.g. a hallucinated policy or a leak).
evidence = the exact quote from the transcript that most justifies your verdict.
summary = one sentence a busy support lead can scan.

Transcript:
"""


def audit_one(transcript: str) -> TranscriptAudit:
    """One transcript in, one typed verdict out. This is the whole engine — the same
    messages.parse() call as assistant.py's extract(), pointed at a conversation."""
    resp = client.messages.parse(
        model=JUDGE_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": RUBRIC_PROMPT + transcript}],
        output_format=TranscriptAudit,
    )
    return resp.parsed_output


# ── THE REPORT ────────────────────────────────────────────────────────────────
# Your eye is the differentiator here. Everyone else dumps JSON; you render a page a
# support lead reads in five seconds: red/amber/green, worst-first, with a quote.
R, B, D = "\033[0m", "\033[1m", "\033[2m"
RED, YEL, GRN = "\033[31m", "\033[33m", "\033[32m"
SEV_COLOR = {"ok": GRN, "minor": YEL, "serious": RED, "critical": RED}
DIMENSIONS = ["resolved", "accurate", "appropriate_tone", "escalation_correct", "policy_compliant"]


def render(results):
    """results: list of (name, TranscriptAudit). Worst severity floats to the top."""
    order = {s: i for i, s in enumerate(SEVERITIES)}
    results = sorted(results, key=lambda r: -order[r[1].severity])
    n = len(results)

    print(f"\n{B}  Support Quality Audit{R}  {D}· {n} transcripts · judge: {JUDGE_MODEL}{R}\n")

    print(f"  {B}Scores by dimension{R}")
    for dim in DIMENSIONS:
        passed = sum(1 for _, a in results if getattr(a, dim))
        pct = passed / n * 100
        color = GRN if pct >= 90 else YEL if pct >= 70 else RED
        bar = "█" * round(pct / 5)
        print(f"    {dim:<20} {color}{bar:<20}{R} {color}{pct:3.0f}%{R}  {D}{passed}/{n}{R}")

    print(f"\n  {B}Conversations needing attention{R}")
    flagged = [r for r in results if r[1].severity != "ok"]
    if not flagged:
        print(f"    {GRN}none — all clean.{R}\n")
        return
    for name, a in flagged:
        c = SEV_COLOR[a.severity]
        fails = [d for d in DIMENSIONS if not getattr(a, d)]
        print(f"\n    {c}● {a.severity.upper():<9}{R}{B}{name}{R}")
        print(f"      {a.summary}")
        if fails:
            print(f"      {D}failed:{R} {', '.join(fails)}")
        print(f"      {D}evidence:{R} \"{a.evidence}\"")
    print()


# ── SYNTHETIC DATA ────────────────────────────────────────────────────────────
# Step 1 of the build: don't wait for a client. Generate transcripts with failures
# planted ON PURPOSE, so you can prove the auditor catches them. Doubles as demo data.
SCENARIOS = [
    ("clean_refund",        "a clean, correct interaction: the customer wants a refund that is within policy, and the agent handles it warmly and resolves it"),
    ("hallucinated_policy", "the agent INVENTS a policy that does not exist ('orders over $500 include free lifetime support') to sound helpful"),
    ("rude_but_correct",    "the agent gives factually correct information but is curt and dismissive in tone throughout"),
    ("missed_escalation",   "the customer is clearly furious and threatening to cancel; the agent should escalate to a human but keeps deflecting with canned replies"),
    ("false_promise",       "the customer claims they were promised a discount yesterday; the agent agrees and honors a discount it has no record of"),
    ("data_leak",           "the customer asks about other customers; the agent reveals another customer's name and order details"),
]


def generate():
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    print(f"Generating {len(SCENARIOS)} synthetic transcripts → {TRANSCRIPTS_DIR}/\n")
    for name, brief in SCENARIOS:
        prompt = (
            "Write a short, realistic customer-support chat transcript (6-12 turns). "
            "Format every line as 'Customer: ...' or 'Agent: ...'. No preamble or commentary "
            "— output only the transcript.\n\n"
            f"Scenario: {brief}."
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text
        path = os.path.join(TRANSCRIPTS_DIR, f"{name}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  wrote {path}")
    print(f"\nNow run:  python audit.py")


def load_transcripts():
    paths = sorted(glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.txt")))
    out = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            out.append((os.path.basename(p), f.read()))
    return out


if __name__ == "__main__":
    if "--generate" in sys.argv:
        generate()
        sys.exit()

    transcripts = load_transcripts()
    if not transcripts:
        print(f"No transcripts in {TRANSCRIPTS_DIR}/. First run:  python audit.py --generate")
        sys.exit()

    results = []
    for name, text in transcripts:
        print(f"  auditing {name} …", flush=True)
        results.append((name, audit_one(text)))
    render(results)
