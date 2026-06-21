# Architecture on paper — a "shipped" assistant

*Module 1 project: map an agent architecture for a problem I care about.*

## The problem

I chronically under-count what I accomplish. The felt sense says "I never
finish anything" while finished things sit right there, unseen. A plain
`done.md` already helps, but it's passive — I have to remember to feed it, and
I'm the one judging what counts, which is exactly the judgment I don't trust at
11pm when the feeling is loudest.

So: an **assistant** that watches my work, decides what actually shipped, and
reflects it back — a mirror that can't turn away. Conversational and proactive,
not a passive log.

## The four faculties

```
PERCEPTION ──► what it can see (read-only)
  • git activity across my repos (commits, pushes, PRs)
  • done.md itself (what's already logged)
  • me telling it "I shipped X"

REASONING ──► the judgments (this is the whole product)
  • shipped, or just activity?
  • doing, or architecting?
  • surface it now, or stay quiet?

ACTION ──► what it can do
  • append a structured entry to done.md
  • ask ONE clarifying question when unsure (not guess)
  • weekly: reflect back — "you shipped 2 things and said you did nothing"

MEMORY ──► what persists
  • done.md = the long-term ledger
  • what it already asked / already ruled, so it doesn't re-litigate
```

**The loop:** observe → judge → act (log / ask / stay silent) → wait → repeat.

## The keystone decision

The assistant is **allowed to overrule me** on what counts as shipped. That only
works if it overrules me with something *external to both* my self-report (the
lying mirror) and raw activity (the counter I rejected). That third thing is a
written rubric I author once, clear-headed, and then neither 11pm-me nor the
agent gets to renegotiate in the moment.

It's a control loop with an external setpoint. The feeling is a drifting sensor;
the rubric is the reference signal.

## The rubric — what counts as shipped

```
SHIPPED if any of:
  ✓ pushed to a public repo — anyone can clone it      ← the everyday bar
  ✓ public / delivered / in someone's hands
  ✓ an open PR to someone else's public repo           ← higher, not daily

NOT shipped:
  ✗ a local commit I never pushed
  ✗ a plan, an outline, a local-only script

Guard:
  · real work, not a whitespace/typo push
```

One test runs through every line: **can someone reach it without me?** Push
clears it; a local commit doesn't. The rubric judges *what counts*, never *how
often* — cadence is a goal I set, not a criterion the rubric enforces. The
moment "shipped" means "every day," the tool punishes me on the day a kid is
sick. Cadence stays out.

## Where it fails

- **Perception** — it can't see ships outside git (a delivered file, a sold
  painting). The mirror goes blind exactly where I need it.
- **Reasoning, too strict** — rules "not shipped" on a real ship. Now my own
  tool says "you did nothing." For me the **false negative is the dangerous
  one** — worse than no tool.
- **Reasoning, gameable** — I start optimizing for the rubric (empty repos with
  nice READMEs) instead of for real work. Goodhart. The activity-counter sneaks
  back through the front door.
- **Action** — it nags, I mute it, dead agent. Right action is mostly silence.
- **Memory** — double-counts, or re-litigates a settled ruling. The count stops
  being trustworthy, which was the whole asset.
- **The loop (the worst one)** — the rubric goes stale. I set it around shippable
  code; six months later my real work is a talk, a course, a client. A
  perfectly-working agent keeps enforcing yesterday's definition of me against
  today's me.

## The daily pulse — a second instrument, walled off

I want a daily signal too — proof the day moved. That's legitimate, it just
isn't a *shipped* question, so it lives beside the rubric, never inside it.

```
  done.md (SHIPPED)            pulse (ACTIVITY)
  ─────────────────           ─────────────────
  strict, external bar        loose, self-reported
  "someone can use it"        "I moved today"
  empty days stay empty       gaps are fine, shown without shame
  the mirror                  the heartbeat
```

The pulse records *any* movement — a local commit, an hour at the desk, a note —
and shows the rhythm **without enforcing it.** It is not a streak with guilt
attached. A gap is true information (a kid was sick), the same way an empty
done.md day is true information. The moment a broken streak makes me feel I
failed, the pulse has become the false-negative failure aimed at my hardest day.

Two instruments, two truths, no contamination: the pulse says *I worked*, done.md
says *I shipped.* Keeping them separate is what lets the rubric stay strict
without the daily silence reading as "nothing."

## The appeal loop — why the agent is trustworthy enough to overrule me

When it rules "not shipped" and I disagree, that's not a fight I lose — it's a
**rubric amendment.** I contest, I win or lose on the merits, and the rubric
*learns my line.* Disagreement upgrades the standard instead of overriding it
once. Without this, a flawless agent slowly becomes a machine for invalidating
my own growth. The appeal loop is the heart of the design.
