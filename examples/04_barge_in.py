"""
Example 04 — barge-in: the human interrupts, and the agent must yield instantly.
================================================================================

This is the feature that separates a real voice agent from a walkie-talkie. In
natural conversation people interrupt — "no wait, actually…" — and a good agent
**stops talking immediately**, throws away the rest of its planned audio, and
starts listening. An agent that keeps talking over you feels broken, and it's the
single most common thing that makes a voice demo feel bad.

We send a long-winded agent response, then have the user cut in partway through.
Watch the session detect the overlapping speech, fire a barge-in, and re-enter
LISTENING mid-sentence — the planned audio after that point is discarded.

Run it:

    python examples/04_barge_in.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice import RealtimeSession, describe, ensure_ready, merge, utterance

ensure_ready()
print(f"Provider: {describe()}\n")

# The user asks for a (long) joke, then cuts in before it finishes.
stream = merge(
    utterance("tell me a joke", start_ms=0),
    utterance("actually what time is it", start_ms=1700),  # interrupts the joke
)

print("User asks for a joke, then interrupts mid-answer:\n")
for e in RealtimeSession(mode="pipeline").run(stream):
    print("  " + e.line())

print(
    "\nThe agent started the joke at 1450ms and the user cut in at 1700ms — so the\n"
    "session fired a BARGE-IN, stopped the response, and treated the new speech as\n"
    "the next turn. The rest of the joke was never 'played'. Two things make this\n"
    "work in production: full-duplex audio (you're still *listening* while you\n"
    "speak, so you hear the interruption), and cancellation that's fast enough to\n"
    "feel instant — cancel the TTS stream and flush the output buffer the moment the\n"
    "user's voice is detected. If you only listened between turns, you couldn't be\n"
    "interrupted at all."
)
