"""
Example 05 — the latency budget: pipeline vs speech-to-speech.
==============================================================

Latency is the make-or-break metric for voice. Humans notice a conversational gap
past ~300–500 ms; much more and the agent feels sluggish or people start talking
over it. So "time to first audio" — from the user stopping to the first sound back
— is the number you engineer against.

This measures it both ways on the same turn: the three-hop pipeline vs a single
speech-to-speech model. Same reply, very different delay, because the pipeline pays
STT + LLM + TTS in series while speech-to-speech pays one hop.

Run it:

    python examples/05_latency_budget.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice import RealtimeSession, describe, ensure_ready, utterance

ensure_ready()
print(f"Provider: {describe()}\n")

frames = utterance("what is the weather today")


def first_audio_latency(mode: str) -> int:
    for e in RealtimeSession(mode=mode).run(frames):
        if e.kind == "response_start":
            return e.latency_ms or 0
    return 0


pipe = first_audio_latency("pipeline")
s2s = first_audio_latency("speech_to_speech")

print("Time to first audio (from the moment the user stops speaking):")
print(f"  pipeline (STT+LLM+TTS)   {pipe:>4}ms")
print(f"  speech-to-speech         {s2s:>4}ms")
print(f"  speech-to-speech is {pipe / s2s:.1f}× faster to first sound\n")

print(
    f"The pipeline's {pipe}ms is three hops stacked; speech-to-speech collapses them\n"
    "into one, which is why it feels more natural in fast back-and-forth. But latency\n"
    "isn't the only axis (example 06): the pipeline gives you a text transcript in the\n"
    "middle to log, moderate, and edit — speech-to-speech hides it. And you can shrink\n"
    "the pipeline's gap a lot by STREAMING each stage so they overlap instead of\n"
    "stacking. Engineer against the number your users feel, not the one on a spec sheet."
)
