"""
Example 02: the STT → LLM → TTS pipeline, and its latency budget.

The first way to build a voice agent is a pipeline of three models in series:

    audio → [STT] → text → [LLM] → text → [TTS] → audio

Each stage adds delay, and they add up. The number the user *feels* is
"time-to-first-audio": how long after they stop talking before they hear anything.
For the pipeline that's the end-pointing wait, then STT + LLM + TTS, all in series.
The end-pointing wait comes first because nothing downstream can start until the
agent decides the user is actually done.

This runs one turn through the pipeline and prints the budget so you can see where
the delay comes from. (Millisecond figures are teaching approximations in
voice/stages.py; the shape, three hops adding three delays, is exact.)

Run it:

    python examples/02_pipeline.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice import RealtimeSession, describe, ensure_ready, utterance
from voice.stages import LLM_LATENCY_MS, STT_LATENCY_MS, TTS_LATENCY_MS, VAD_SILENCE_MS

ensure_ready()
print(f"Provider: {describe()}\n")

TOTAL_MS = VAD_SILENCE_MS + STT_LATENCY_MS + LLM_LATENCY_MS + TTS_LATENCY_MS

print("The budget, from the user's last word to the first sound back:")
print(f"  end-pointing silence (VAD)  {VAD_SILENCE_MS:>4}ms   nothing starts before this")
print(f"  STT (finalize transcript)   {STT_LATENCY_MS:>4}ms")
print(f"  LLM (first reply token)     {LLM_LATENCY_MS:>4}ms")
print(f"  TTS (first audio chunk)     {TTS_LATENCY_MS:>4}ms")
print(f"  {'-'*32}")
print(f"  time to first audio         {TOTAL_MS:>4}ms  (all in series)\n")

print("One turn through the pipeline:")
for e in RealtimeSession(mode="pipeline").run(utterance("what is the weather today")):
    print("  " + e.line())

print(
    f"\nThat {TOTAL_MS}ms of dead air is the pipeline's core problem, and three models can't\n"
    "each be instant. Two things fight it: STREAMING every stage (start the LLM on a\n"
    "partial transcript, start TTS on the first LLM tokens, so the stages overlap\n"
    "instead of stacking), and picking a single speech-to-speech model instead\n"
    "(examples 05-06). Tightening the VAD window fights it too, at the cost of cutting\n"
    "people off mid-thought. The pipeline's payoff is CONTROL: there's a text\n"
    "transcript in the middle you can log, moderate, and edit."
)
