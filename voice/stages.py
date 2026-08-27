"""
voice/stages.py: the two architectures, as latency-annotated stages.

There are two ways to build a voice agent, and choosing between them is the central
design decision of this dive:

  PIPELINE          audio → [STT] → text → [LLM] → text → [TTS] → audio
  SPEECH-TO-SPEECH  audio → [one multimodal model] → audio

The pipeline is three models in series; speech-to-speech is one. That difference is
mostly about **latency** (each hop adds delay) and **control** (the pipeline exposes
a text transcript you can log, moderate, and edit; speech-to-speech hides it). This
file models each stage as a deterministic transform with a latency budget in
milliseconds, so the examples can *add up* the delay and compare the two designs
offline. The budget starts before either architecture does, with the end-pointing
silence (VAD_SILENCE_MS) both of them wait through. The millisecond figures are
teaching approximations. Real numbers vary by model, network, and audio length, but
the *shape* (more hops = more delay) is exact.
"""

from __future__ import annotations

from dataclasses import dataclass

# Rough per-stage "time to first output" budgets, in milliseconds. These are the
# delay from "input ready" to "this stage starts producing output".
STT_LATENCY_MS = 300     # finalize a transcript after the user stops speaking
LLM_LATENCY_MS = 500     # time to the first token of the reply
TTS_LATENCY_MS = 200     # time to the first chunk of synthesized audio
S2S_LATENCY_MS = 500     # a single speech-to-speech model, first audio out

# End-pointing: how long a run of silence must be before the agent concludes the
# user is done. Nothing downstream can start until this fires, so it is the first
# line of the budget and, in production, often the largest one. It is also the only
# entry BOTH architectures pay: the pipeline and speech-to-speech are equally stuck
# behind it, which is why the gap between them is narrower than the model latencies
# alone suggest. Shrinking it makes the agent snappier and more likely to cut people
# off mid-thought; that dial is a product decision, not a tuning detail.
VAD_SILENCE_MS = 500

TTS_WORD_MS = 150        # how long each spoken word takes to play back


def transcribe(words: list[str]) -> str:
    """Mock STT: frames of speech → a transcript string."""
    return " ".join(words)


# A tiny canned "brain" so a reply is deterministic and offline.
_REPLIES = {
    "weather": "It's sunny and seventy two degrees today.",
    "time": "It's a quarter past three.",
    "name": "I'm your voice assistant, nice to meet you.",
    "joke": "Why did the function return early? It had a great exit strategy.",
    "hello": "Hi there! How can I help you today?",
}


def respond(transcript: str) -> str:
    """Mock LLM: transcript → reply text (keyword-matched, deterministic)."""
    low = transcript.lower()
    for key, reply in _REPLIES.items():
        if key in low:
            return reply
    return "Sorry, I didn't catch that. Could you say it another way?"


def speak_duration_ms(reply: str) -> int:
    """Mock TTS: how long the reply takes to play, given one word ≈ TTS_WORD_MS."""
    return max(1, len(reply.split())) * TTS_WORD_MS


@dataclass
class ResponsePlan:
    """A planned spoken response: what to say, how long the processing takes before
    the first audio comes out, and how long that audio plays.

    `first_audio_ms` is processing only, so it isolates the architecture. The gap the
    user actually feels adds the end-pointing wait on top; the session computes it."""

    text: str
    first_audio_ms: int   # processing latency, from turn detected to first audio out
    duration_ms: int      # total playback time


def plan_pipeline(transcript: str) -> ResponsePlan:
    """Plan a response using the STT → LLM → TTS pipeline. First audio waits on all
    three stages in series (and, before them, on end-pointing)."""
    reply = respond(transcript)
    first = STT_LATENCY_MS + LLM_LATENCY_MS + TTS_LATENCY_MS
    return ResponsePlan(text=reply, first_audio_ms=first, duration_ms=speak_duration_ms(reply))


def plan_speech_to_speech(transcript: str) -> ResponsePlan:
    """Plan a response using a single speech-to-speech model. One hop, so first
    audio comes out much sooner."""
    reply = respond(transcript)
    return ResponsePlan(text=reply, first_audio_ms=S2S_LATENCY_MS, duration_ms=speak_duration_ms(reply))
