"""
voice/providers.py: this dive is an offline simulator.

Unlike its sibling repos, this dive does not switch between OpenAI and Claude,
because a genuine realtime voice session needs low-latency, full-duplex audio I/O
(a microphone and speaker, a WebSocket or WebRTC transport) that can't be shown
honestly in a small, from-scratch, offline teaching example. So the whole repo runs
on a deterministic **mock**: simulated audio frames and simulated per-stage latency
let you see the turn-taking, barge-in, and latency mechanics exactly, for $0, with
no key.

What maps to production: the state machine (session.py), the two architectures
(stages.py), and the barge-in/latency reasoning are all real. The transport is what
the mock stands in for. In production you'd use a speech-to-speech API over
WebSocket or WebRTC (OpenAI's Realtime API, Google's Gemini Live API) or an
STT→LLM→TTS pipeline wired to streaming vendors. The README's "From teaching code
to production" section maps each piece.

We keep the familiar `provider_name` / `describe` / `ensure_ready` shape so the
examples read like the rest of the series; there's just one provider here: `mock`.
"""

from __future__ import annotations

import os

_MOCK_MODEL = "mock-voice-1"


def provider_name() -> str:
    return os.getenv("PROVIDER", "mock").strip().lower()


def describe() -> str:
    return f"mock  (offline realtime simulator, model={_MOCK_MODEL}, no key)"


def ensure_ready() -> None:
    """Never fails; this dive is a fully offline simulator. Present for parity
    with the sibling repos' setup pattern."""
    p = provider_name()
    if p != "mock":
        print(
            f"(note: PROVIDER={p!r}; this dive is an offline simulator and always runs "
            f"on the mock. See the README for wiring a real Realtime API.)"
        )
