# assistant.py — rung 5. The four ideas, composed into one running thing.
#
#   MEMORY      → `messages` persists across turns (the REPL loop never drops it)
#   STREAMING   → replies print token-by-token as they arrive
#   TOOLS       → Claude can call your functions, and we run the loop until it's done
#   STRUCTURED  → `extract` is a tool whose job is to return validated, typed data
#
# It's a baby Claude Code: you type, it remembers, it streams, it reaches for a tool.

import os
import sys
import select
import json
from dotenv import load_dotenv
from pydantic import BaseModel
import anthropic

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-opus-4-8"


# 1. THE TOOLS — plain Python you control (same idea as 04_agent.py).
def add(a: float, b: float) -> float:
    return a + b


def multiply(a: float, b: float) -> float:
    return a * b


# Structured output, packaged AS a tool. When Claude calls `extract`, this runs a
# SEPARATE .parse() call (rung 3) and hands back typed JSON — so the chat loop stays
# uniform: everything is "Claude asks for a tool, we run it, we feed the result back".
class ActionItem(BaseModel):
    task: str
    owner: str          # "unknown" if not stated
    due: str            # "none" if not stated


class Extraction(BaseModel):
    gist: str
    action_items: list[ActionItem]


def extract(text: str) -> str:
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": f"Pull the gist and any action items:\n\n{text}"}],
        output_format=Extraction,
    )
    return resp.parsed_output.model_dump_json(indent=2)


TOOL_IMPLS = {"add": add, "multiply": multiply, "extract": extract}

# 2. THE SCHEMAS — how Claude "sees" the tools (name, purpose, inputs).
TOOLS = [
    {
        "name": "add",
        "description": "Add two numbers.",
        "input_schema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "multiply",
        "description": "Multiply two numbers.",
        "input_schema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "extract",
        "description": "Pull a gist and structured action items out of notes, an email, or a transcript.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The raw text to extract from."}},
            "required": ["text"],
        },
    },
]


# A clean startup banner. \033[1m = bold, \033[2m = dim, \033[36m = cyan,
# \033[0m = reset back to normal. Same ANSI escapes as the spinner in 03_extract.py.
def banner():
    B, D, C, R = "\033[1m", "\033[2m", "\033[36m", "\033[0m"
    print(f"""
  {C}▟▙{R}  {B}assistant{R}  {D}· the 4 rungs, composed{R}
  {C}▜▛{R}  {D}{MODEL} · streaming · tools · memory{R}
      {D}{os.getcwd()}{R}

  {D}Try{R} "what is 23 * 17, plus 100?"
  {D}/reset{R} clears memory   {D}/exit{R} or Ctrl-D quits
""")


def read_input():
    """Read a turn. If a paste has queued extra lines behind the first one, drain
    them so the whole block is ONE message — not one runaway turn per line."""
    first = input("you › ")
    lines = [first]
    while select.select([sys.stdin], [], [], 0)[0]:   # is more already buffered?
        line = sys.stdin.readline()
        if not line:
            break
        lines.append(line.rstrip("\n"))
    return "\n".join(lines).strip()


# 3. THE REPL — keep the conversation alive. `messages` IS the memory; we never reset
# it between turns (that's why Claude remembers what you said three messages ago).
messages = []
banner()

while True:
    try:
        user = read_input()     # gathers a whole paste into one message
    except EOFError:            # Ctrl-D
        print()
        break

    if not user:
        continue
    if user in ("/exit", "/quit"):
        break
    if user == "/reset":
        messages = []
        print("(memory cleared)\n")
        continue

    messages.append({"role": "user", "content": user})

    # 4. THE AGENT LOOP — stream the reply; if Claude asked for tools, run them and
    # loop again so it can use the results. Break once it stops asking for tools.
    while True:
        print("assistant › ", end="", flush=True)
        with client.messages.stream(
            model=MODEL,
            max_tokens=1000,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            reply = stream.get_final_message()   # full message: content + stop_reason
        print()

        # Record what Claude said (text and/or tool_use blocks) — part of memory.
        messages.append({"role": "assistant", "content": reply.content})

        if reply.stop_reason != "tool_use":
            break   # Claude has its final answer for this turn

        results = []
        for block in reply.content:
            if block.type == "tool_use":
                output = TOOL_IMPLS[block.name](**block.input)
                print(f"  [tool] {block.name}({block.input})")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,   # must match the request's id
                    "content": str(output),
                })
        messages.append({"role": "user", "content": results})

    print()
