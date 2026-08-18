"""
Example 01: audio is a stream of frames (offline).

The first mental shift for realtime voice: you never have "the recording." Audio
arrives as a continuous stream of tiny frames (~10-20 ms each), and you work with
the frames you have *so far*. Turn detection, interruption, and latency all fall
out of that fact.

Here we build one simulated utterance as frames (a speech frame per word, then a
run of silence) and watch a simple voice-activity rule find the end of the turn.
(Our frames carry a word of text as a stand-in for ~20 ms of audio; real frames
carry PCM samples. The streaming shape is identical.)

Run it:

    python examples/01_audio_is_frames.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice import describe, ensure_ready, segment, utterance

ensure_ready()
print(f"Provider: {describe()}\n")

VAD_SILENCE_MS = 500  # this much continuous silence after speech = "turn is over"

frames = utterance("what is the weather today", word_ms=150, trailing_silence_ms=600)
speech = [f for f in frames if f.kind == "speech"]
silence = [f for f in frames if f.kind == "silence"]

print(f"The utterance is {len(frames)} frames: {len(speech)} speech + {len(silence)} silence.\n")
print("First few frames (t, kind, word):")
for f in frames[:7]:
    print(f"  {f.t_ms:>4}ms  {f.kind:<7} {f.text}")
print("  ...")

utts = segment(frames, VAD_SILENCE_MS)
turn = utts[0]
print(f"\nVAD (>= {VAD_SILENCE_MS}ms of silence) closed the turn:")
print(f"  speech ran {turn.start_ms}–{turn.end_ms}ms, transcript = {' '.join(turn.words)!r}")
print(f"  but the turn is only *detected* at {turn.end_ms + VAD_SILENCE_MS}ms, once the silence run is long enough")

print(
    "\nThat's the whole substrate of realtime voice: frames in, frames out, always\n"
    "'so far'. Deciding the user is *done* (turn detection) is a judgment call over\n"
    "silence. Too eager and you cut them off, too patient and the agent feels slow.\n"
    "Note the gap between the last word and the detection: that silence window is\n"
    "pure waiting, nothing downstream can start inside it, and so it is the first\n"
    "line of the latency budget in example 02, and the one line both architectures\n"
    "pay alike. Everything in this dive is built on this stream."
)
