import sys
from dotenv import load_dotenv
import anthropic

load_dotenv()  # loads ANTHROPIC_API_KEY from the .env file into the environment
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from your environment

# CONCEPT: streaming.
# summarize.py waits for the WHOLE answer, then prints it. For long answers that
# feels like a hang. Streaming hands you tokens as they're generated, so output
# starts immediately. Same request — you just consume it as a live stream.

print("Paste your text, then press Ctrl-D:\n")
text = sys.stdin.read()

if not text.strip():
    print("No text given. Nothing to do.")
    sys.exit()

print("\n----- SUMMARY (streaming) -----\n")

# `client.messages.stream(...)` is a context manager. `stream.text_stream`
# yields text chunks as they arrive. flush=True forces them to the screen now.
with client.messages.stream(
    model="claude-opus-4-8",          # swap to claude-haiku-4-5 for cheap+fast
    max_tokens=1000,
    system="You summarize pasted text clearly. "
           "Lead with a one-line gist, then 3-6 bullets of the key ideas.",
    messages=[{"role": "user", "content": f"Summarize this:\n\n{text}"}],
) as stream:
    for chunk in stream.text_stream:
        print(chunk, end="", flush=True)

    # After the loop you can still get the complete message (usage, stop reason, ...)
    final = stream.get_final_message()

print(f"\n\n[done — {final.usage.output_tokens} output tokens]")
