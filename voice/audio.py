"""
voice/audio.py — audio is a stream of frames, not a file.
=========================================================

The first mental shift for realtime voice: audio isn't a blob you upload and wait
on — it's a **continuous stream of small frames** (typically 10–20 ms each) flowing
in both directions at once. You never have "the whole recording"; you have the
frames so far. Everything else (turn detection, interruption, latency) follows from
that.

To keep this dive offline and deterministic, a frame here carries a *word* of text
as a stand-in for ~20 ms of PCM audio, plus a timestamp in milliseconds. A real
frame carries raw audio samples; the timing and the streaming shape are the same.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Frame:
    """One slice of the audio stream at time `t_ms`.

    kind "speech" carries a word (our stand-in for audio energy); kind "silence"
    carries nothing and is what a voice-activity detector uses to find the end of a
    turn."""

    t_ms: int
    kind: str  # "speech" | "silence"
    text: str = ""


def utterance(words: str, *, start_ms: int = 0, word_ms: int = 150, trailing_silence_ms: int = 600,
              frame_ms: int = 20) -> list[Frame]:
    """Build a simulated spoken utterance: one speech frame per word (spaced
    `word_ms` apart), then a run of silence frames so a VAD can detect the turn end.

    Returns frames in time order. `frame_ms` is the silence-frame granularity."""
    frames: list[Frame] = []
    t = start_ms
    for w in words.split():
        frames.append(Frame(t_ms=t, kind="speech", text=w))
        t += word_ms
    # Trailing silence, one frame every `frame_ms`.
    end_speech = t
    while t < end_speech + trailing_silence_ms:
        frames.append(Frame(t_ms=t, kind="silence"))
        t += frame_ms
    return frames


def merge(*streams: list[Frame]) -> list[Frame]:
    """Merge several frame streams into one, sorted by time — e.g. to place a
    barge-in utterance partway through the conversation."""
    return sorted((f for s in streams for f in s), key=lambda f: f.t_ms)
