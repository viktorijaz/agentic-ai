#!/usr/bin/env python3
"""summarize.py — paste text or pass a file, get a summary. The dumbest agent that works.

Usage:
    python summarize.py                 # paste text, then Ctrl-D
    python summarize.py article.txt     # summarize a file
    python summarize.py article.txt --deep   # use the strongest model for hard text
"""
import sys
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from your environment

# --- pick the model: Sonnet by default, Opus when you ask for --deep ---
args = [a for a in sys.argv[1:] if a != "--deep"]
deep = "--deep" in sys.argv
model = "claude-opus-4-8" if deep else "claude-sonnet-4-6"

# 1. INPUT — from a file if you named one, otherwise from whatever you paste
if args:
    with open(args[0], "r", encoding="utf-8") as f:
        text = f.read()
else:
    print("Paste your text, then press Ctrl-D (Ctrl-Z + Enter on Windows):\n")
    text = sys.stdin.read()

if not text.strip():
    print("No text given. Nothing to summarize.")
    sys.exit()

# 2. THINK — send it to the model with a clear instruction (the prompt IS the program)
message = client.messages.create(
    model=model,
    max_tokens=1500,   # caps the SUMMARY length (~1100 words), not your input
    system="You summarize text clearly and faithfully. "
           "Lead with a one-line gist, then 3-8 bullets of the key ideas, "
           "then one line on anything important the text leaves out or assumes.",
    messages=[
        {"role": "user", "content": f"Summarize this:\n\n{text}"}
    ],
)

# 3. ACT — do something with the answer (here: just print it)
print(f"\n----- SUMMARY ({model}) -----\n")
print(message.content[0].text)
