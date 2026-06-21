# NOTE: the API is stateless — Claude remembers nothing between calls. Each
# create() is a fresh request, so the ONLY memory is the `messages` list we resend
# in full every loop. That's why cost grows per turn, why the context window is a
# ceiling (eventually trim/summarize), and why prompt caching exists.

import sys
from dotenv import load_dotenv
import anthropic
import json

load_dotenv()  # loads ANTHROPIC_API_KEY from the .env file into the environment
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from your environment

# CONCEPT: tool use — the actual "agent" loop.
# So far Claude only TALKS. A tool lets it ACT: you describe functions Claude may
# call, and when it asks to call one, YOUR code runs it and feeds the result back.
# Claude loops — call tool, see result, maybe call again — until it can answer.
# That loop is what makes this folder "agents".


# 1. THE TOOLS — plain Python functions you control.
def add(a: float, b: float) -> float:
    return a + b


def multiply(a: float, b: float) -> float:
    return a * b


TOOL_IMPLS = {"add": add, "multiply": multiply}

# 2. THE SCHEMAS — how Claude "sees" those tools (name, what it does, inputs).
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
]

question = " ".join(sys.argv[1:]) or "What is 23 * 17, plus 100?"
print(f"Q: {question}\n")

messages = [{"role": "user", "content": question}]

# 3. THE AGENT LOOP — keep going until Claude stops asking for tools.
i = 0
while True:
    i = i+1
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1000,
        tools=TOOLS,
        messages=messages,
    )

    if response.stop_reason != "tool_use":
        break  # Claude has its final answer

    # Record what Claude said (includes the tool_use request), then run the tools.
    messages.append({"role": "assistant", "content": response.content})

    results = []
    for block in response.content:
        if block.type == "tool_use":
            output = TOOL_IMPLS[block.name](**block.input)
            print(f"  [tool] {block.name}({block.input}) = {output}")
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,   # must match the request's id
                "content": str(output),
            })
    

    # Send every result back in ONE user message, then loop.
    messages.append({"role": "user", "content": results})

    print(f"messages[{i}]: {json.dumps(messages, indent=2, default=str)}")



answer = next((b.text for b in response.content if b.type == "text"), "")
print(f"\nA: {answer}")
