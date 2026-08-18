"""
voice/session.py: the turn-taking state machine (with barge-in).

A realtime voice agent is a small state machine over a full-duplex stream:

    LISTENING ──(user stops: VAD sees enough silence)──▶ THINKING
    THINKING  ──(first audio ready)──────────────────────▶ SPEAKING
    SPEAKING  ──(response finishes)──────────────────────▶ LISTENING
    SPEAKING  ──(USER STARTS TALKING again = barge-in)───▶ LISTENING  (cancel output)

The two hard parts, both handled here:

  1. Turn detection: deciding the user is *done* talking. We use a simple
     voice-activity rule: a run of silence longer than `vad_silence_ms` after
     speech ends the turn. (Real systems use a trained VAD / end-pointing model.)
     Nothing downstream starts until this fires, so that wait is the first entry in
     every latency budget, and the one both architectures pay alike.
  2. Barge-in: the human interrupts while the agent is speaking. A good voice
     agent stops *immediately*, discards the rest of its planned audio, and starts
     listening. An agent that talks over the user feels broken.

`RealtimeSession.run(frames)` consumes a merged input stream (see audio.merge) and
returns a timeline of `Event`s with millisecond timestamps, deterministic, so you
can read the exact turn-taking and interruption behavior offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .audio import Frame
from .stages import VAD_SILENCE_MS, ResponsePlan, plan_pipeline, plan_speech_to_speech, transcribe


@dataclass
class Event:
    t_ms: int
    kind: str
    text: str = ""
    # Set on response_start: the gap the user feels, from their last word to the
    # first sound back. That is the end-pointing wait plus the processing latency.
    latency_ms: int | None = None

    def line(self) -> str:
        stamp = f"[{self.t_ms:>5}ms]"
        if self.kind == "user_speech_start":
            return f"{stamp} 🎙  user starts speaking"
        if self.kind == "user_speech_end":
            return f"{stamp} 🎙  user stops: {self.text!r}"
        if self.kind == "response_start":
            return f"{stamp} 🔊 agent speaks (first audio {self.latency_ms}ms after the user stopped): {self.text!r}"
        if self.kind == "response_end":
            return f"{stamp} ✓  agent finished speaking"
        if self.kind == "interrupted":
            return f"{stamp} ✋ BARGE-IN: {self.text}"
        return f"{stamp} {self.kind} {self.text}"


@dataclass
class Utterance:
    start_ms: int
    end_ms: int
    words: list[str] = field(default_factory=list)


def segment(frames: list[Frame], vad_silence_ms: int) -> list[Utterance]:
    """Group a frame stream into utterances using the silence-based VAD rule.

    `frames` must be in time order (audio.merge sorts for you). An utterance's
    `end_ms` is when its last word finishes playing, not when it starts, so the
    silence run is measured from real end-of-speech."""
    utterances: list[Utterance] = []
    cur: Utterance | None = None
    speech_end_t = None
    for f in frames:
        if f.kind == "speech":
            if cur is None:
                cur = Utterance(start_ms=f.t_ms, end_ms=f.t_ms)
            cur.words.append(f.text)
            speech_end_t = f.t_ms + f.duration_ms
            cur.end_ms = speech_end_t
        else:  # silence
            if cur is not None and speech_end_t is not None and f.t_ms - speech_end_t >= vad_silence_ms:
                utterances.append(cur)
                cur = None
                speech_end_t = None
    if cur is not None:
        utterances.append(cur)
    return utterances


class RealtimeSession:
    """A turn-taking session in one of two modes: 'pipeline' or 'speech_to_speech'."""

    def __init__(self, mode: str = "pipeline", *, vad_silence_ms: int = VAD_SILENCE_MS):
        if mode not in ("pipeline", "speech_to_speech"):
            raise ValueError("mode must be 'pipeline' or 'speech_to_speech'")
        self.mode = mode
        self.vad_silence_ms = vad_silence_ms

    def _plan(self, transcript: str) -> ResponsePlan:
        return plan_pipeline(transcript) if self.mode == "pipeline" else plan_speech_to_speech(transcript)

    def run(self, frames: list[Frame]) -> list[Event]:
        utterances = segment(frames, self.vad_silence_ms)
        events: list[Event] = []
        for i, utt in enumerate(utterances):
            transcript = transcribe(utt.words)
            events.append(Event(utt.start_ms, "user_speech_start"))
            events.append(Event(utt.end_ms, "user_speech_end", text=transcript))

            plan = self._plan(transcript)
            # Nothing can start until end-pointing decides the turn is over, so the
            # felt gap is that wait plus the architecture's processing latency.
            felt_latency = self.vad_silence_ms + plan.first_audio_ms
            resp_start = utt.end_ms + felt_latency
            resp_end = resp_start + plan.duration_ms

            next_start = utterances[i + 1].start_ms if i + 1 < len(utterances) else None

            if next_start is not None and next_start <= resp_start:
                # User spoke again before the agent produced any audio, so the turn is
                # superseded. A responsive agent abandons the planned reply.
                events.append(Event(next_start, "interrupted",
                                    text="user spoke before the agent's audio started; planned reply dropped"))
            elif next_start is not None and next_start < resp_end:
                # Classic barge-in: the agent was mid-sentence when the user cut in.
                events.append(Event(resp_start, "response_start", text=plan.text, latency_ms=felt_latency))
                events.append(Event(next_start, "interrupted",
                                    text="user cut in mid-response; agent stops and listens"))
            else:
                events.append(Event(resp_start, "response_start", text=plan.text, latency_ms=felt_latency))
                events.append(Event(resp_end, "response_end"))
        return sorted(events, key=lambda e: e.t_ms)
