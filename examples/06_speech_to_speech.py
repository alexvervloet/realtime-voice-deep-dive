"""
Example 06 — speech-to-speech: one model, and when to choose it.
================================================================

Speech-to-speech uses a single multimodal model that hears audio and speaks audio
directly — no transcript in the middle:

    audio → [one model] → audio

It wins on the two things pipelines struggle with: **latency** (one hop, example
05) and **naturalness** (it hears tone, pacing, and emotion, and can speak with
them — nuance a transcript throws away). What it gives up is **control and
observability**: there's no text step to log, moderate, redact, or hand to a tool,
and steering it is harder.

This runs the same short conversation speech-to-speech, then lays out the decision.
There's no universally right answer — it's a real tradeoff you make per product.

Run it:

    python examples/06_speech_to_speech.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice import RealtimeSession, describe, ensure_ready, merge, utterance

ensure_ready()
print(f"Provider: {describe()}\n")

stream = merge(
    utterance("hello there", start_ms=0),
    utterance("what is the weather today", start_ms=3000),
)

print("A conversation, speech-to-speech (one model, low latency):\n")
for e in RealtimeSession(mode="speech_to_speech").run(stream):
    print("  " + e.line())

print("\nChoosing between the two architectures:\n")
print("  Reach for SPEECH-TO-SPEECH when latency and naturalness dominate —")
print("    consumer voice assistants, companions, hands-free chat. Fewer moving parts.")
print("  Reach for the PIPELINE when you need the transcript — to enforce guardrails")
print("    and moderation, call tools/RAG on the text, keep an auditable log, or")
print("    swap any stage's vendor independently. Common in support and agentic voice.")
print("  Many production systems are HYBRID: speech-to-speech for the conversational")
print("    turn, with a parallel transcript for logging and safety.")

print(
    "\nSame decision discipline as the rest of the series: pick the simplest\n"
    "architecture that meets your real constraints — here, latency and naturalness vs\n"
    "control and observability — not the newest one on the spec sheet."
)
