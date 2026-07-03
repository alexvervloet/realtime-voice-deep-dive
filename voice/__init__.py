"""
voice — a from-scratch, offline simulator for realtime voice agents.

Realtime voice can't be shown honestly in a tiny offline example if it needs real
mic/speaker I/O — so this repo simulates the *mechanics* deterministically:

  audio.py    — audio as a stream of timestamped frames (+ builders)
  stages.py   — the two architectures as latency-annotated stages (pipeline vs S2S)
  session.py  — the turn-taking state machine, with VAD turn detection + barge-in
  providers.py— the (mock-only) provider shim, for parity with the series

Typical use:

    from voice import RealtimeSession, utterance
    events = RealtimeSession(mode="pipeline").run(utterance("what is the weather"))
    for e in events:
        print(e.line())
"""

from .audio import Frame, merge, utterance
from .providers import describe, ensure_ready, provider_name
from .session import Event, RealtimeSession, Utterance, segment
from .stages import (
    LLM_LATENCY_MS,
    S2S_LATENCY_MS,
    STT_LATENCY_MS,
    TTS_LATENCY_MS,
    ResponsePlan,
    plan_pipeline,
    plan_speech_to_speech,
    respond,
    speak_duration_ms,
    transcribe,
)

__all__ = [
    "Frame",
    "utterance",
    "merge",
    "RealtimeSession",
    "Event",
    "Utterance",
    "segment",
    "ResponsePlan",
    "plan_pipeline",
    "plan_speech_to_speech",
    "respond",
    "transcribe",
    "speak_duration_ms",
    "STT_LATENCY_MS",
    "LLM_LATENCY_MS",
    "TTS_LATENCY_MS",
    "S2S_LATENCY_MS",
    "describe",
    "ensure_ready",
    "provider_name",
]
