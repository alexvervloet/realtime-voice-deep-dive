"""
Example 03 — the turn-taking state machine over a short dialogue.
=================================================================

A voice agent is a state machine over a full-duplex stream:

    LISTENING → (user stops) → THINKING → (first audio) → SPEAKING → (done) → LISTENING

This runs a clean back-and-forth — three user turns, no interruptions — so you can
watch the machine cycle. Each turn: the VAD closes the user's speech, the agent
thinks, speaks, and returns to listening before the next turn begins.

Run it:

    python examples/03_turn_taking.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice import RealtimeSession, describe, ensure_ready, merge, utterance

ensure_ready()
print(f"Provider: {describe()}\n")

# Three turns, spaced so each agent response finishes before the next turn starts
# (no barge-in here — that's example 04).
dialogue = merge(
    utterance("hello there", start_ms=0),
    utterance("what is the weather today", start_ms=4000),
    utterance("tell me a joke", start_ms=9000),
)

print("A polite, non-overlapping conversation:\n")
state = "LISTENING"
for e in RealtimeSession(mode="pipeline").run(dialogue):
    # Track the state the event implies, to make the machine visible.
    if e.kind == "user_speech_start":
        state = "LISTENING"
    elif e.kind == "user_speech_end":
        state = "THINKING"
    elif e.kind == "response_start":
        state = "SPEAKING"
    elif e.kind == "response_end":
        state = "LISTENING"
    print(f"  {state:<9} {e.line()}")

print(
    "\nOne clean cycle per turn: LISTENING → THINKING → SPEAKING → LISTENING. Real\n"
    "conversations aren't this tidy — people interrupt, and the agent has to yield\n"
    "instantly. That's barge-in, next."
)
