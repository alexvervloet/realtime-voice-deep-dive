"""
Example 05: the latency budget: pipeline vs speech-to-speech.

Latency is the make-or-break metric for voice. Humans notice a conversational gap
past ~300–500 ms; much more and the agent feels sluggish or people start talking
over it. So "time to first audio", from the user stopping to the first sound back,
is the number you engineer against.

This measures it both ways on the same turn: the three-hop pipeline vs a single
speech-to-speech model. Same reply, different delay, because the pipeline pays
STT + LLM + TTS in series while speech-to-speech pays one hop. Both first wait out
the same end-pointing window, which is why the honest ratio is smaller than a
comparison of model latencies alone would suggest.

Run it:

    python examples/05_latency_budget.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice import RealtimeSession, describe, ensure_ready, utterance
from voice.stages import VAD_SILENCE_MS

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

def ms(v: int) -> str:
    return f"{v}ms"


print("Time to first audio, from the user's last word to the first sound back:\n")
print(f"  {'':<24}{'end-pointing':>14}{'processing':>13}{'felt':>10}")
print(f"  {'pipeline (STT+LLM+TTS)':<24}{ms(VAD_SILENCE_MS):>14}{ms(pipe - VAD_SILENCE_MS):>13}{ms(pipe):>10}")
print(f"  {'speech-to-speech':<24}{ms(VAD_SILENCE_MS):>14}{ms(s2s - VAD_SILENCE_MS):>13}{ms(s2s):>10}")
print(f"\n  Overall, speech-to-speech is {pipe / s2s:.1f}× faster to first sound. On the")
print(f"  processing it actually controls, it is {(pipe - VAD_SILENCE_MS) / (s2s - VAD_SILENCE_MS):.1f}× faster.\n")

print(
    "The pipeline's processing is three hops stacked; speech-to-speech collapses them\n"
    "into one, which is why it feels more natural in fast back-and-forth. But notice\n"
    "what the third column does to the sales pitch: both designs wait out the same\n"
    "end-pointing window before either of them starts, so the advantage the user\n"
    "actually hears is smaller than a comparison of the models alone would suggest.\n"
    "Latency isn't the only axis either (example 06): the pipeline gives you a text\n"
    "transcript in the middle to log, moderate, and edit; speech-to-speech hides it.\n"
    "And you can shrink the pipeline's gap a lot by STREAMING each stage so they\n"
    "overlap instead of stacking. Engineer against the number your users feel, not\n"
    "the one on a spec sheet."
)
