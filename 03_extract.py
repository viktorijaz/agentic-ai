import sys
import time
import threading
import itertools
from dotenv import load_dotenv
from pydantic import BaseModel
import anthropic

load_dotenv()  # loads ANTHROPIC_API_KEY from the .env file into the environment
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from your environment


# A spinner so the wait isn't dead silence. It runs on its own thread, printing a
# frame every 0.1s, until we tell it to stop. `\r` returns to the line start so each
# frame overwrites the last; on stop we clear the line so the real output is clean.
def spinner(stop_event, label="thinking…"):
    for frame in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        if stop_event.is_set():
            break
        print(f"\r{frame} {label}", end="", flush=True)
        time.sleep(0.1)
    print("\r\033[K", end="", flush=True)  # \033[K clears from cursor to end of line

# CONCEPT: structured outputs.
# summarize.py gives you PROSE — fine for a human, useless to code. Here we hand
# Claude a schema (a Pydantic model) and get back a VALIDATED object with typed
# fields. This is the bridge from "AI" to "automation": once the answer is data,
# the next line of your program can act on it (save it, route it, total it...).


# 1. SCHEMA — describe the shape you want back.
class ActionItem(BaseModel):
    task: str
    owner: str          # who should do it ("unknown" if not stated)
    due: str            # when ("none" if not stated)


class Extraction(BaseModel):
    gist: str
    action_items: list[ActionItem]


# INPUT — from a file if you named one (python 03_extract.py sample_notes.txt),
# otherwise from whatever you paste.
args = sys.argv[1:]
if args:
    with open(args[0], "r", encoding="utf-8") as f:
        text = f.read()
else:
    print("Paste notes / an email / a transcript, then press Ctrl-D:\n")
    text = sys.stdin.read()

if not text.strip():
    print("No text given. Nothing to do.")
    sys.exit()

# 2. THINK — .parse() sends the schema AND validates the reply against it.
# Start the spinner, make the (blocking) call, then always stop the spinner —
# the try/finally guarantees we stop it even if the call raises an error.
stop_event = threading.Event()
spin = threading.Thread(target=spinner, args=(stop_event,))
spin.start()
try:
    response = client.messages.parse(
        model="claude-opus-4-8",          # swap to claude-haiku-4-5 for cheap+fast
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"Pull the gist and any action items from this:\n\n{text}",
        }],
        output_format=Extraction,
    )
finally:
    stop_event.set()
    spin.join()

# 3. ACT — response.parsed_output is a real Extraction instance, not a string.
result = response.parsed_output
print(f"\nGist: {result.gist}\n")
if not result.action_items:
    print("No action items found.")
for i, item in enumerate(result.action_items, 1):
    print(f"{i}. {item.task}  (owner: {item.owner}, due: {item.due})")
