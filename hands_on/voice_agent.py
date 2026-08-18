"""
Capstone: a simulated realtime voice agent you can drive.

Everything assembled: the turn-taking state machine, both architectures, the
latency readout, and a barge-in demo, wired to a CLI. It's a *simulator* (typed
turns stand in for speech; see the README for why realtime voice can't be shown
honestly offline otherwise), but the mechanics are the real ones.

    # Interactive: type a line = one user turn; see the reply and its latency.
    #   (type 'quit' to exit)
    python hands_on/voice_agent.py

    # Pick the architecture:
    python hands_on/voice_agent.py --mode speech_to_speech

    # Run the built-in barge-in demo (a scripted interruption):
    python hands_on/voice_agent.py --demo barge-in

    # Run a clean multi-turn demo:
    python hands_on/voice_agent.py --demo dialogue
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from voice import Frame, RealtimeSession, describe, ensure_ready, merge, utterance


# The scripted demos live here as named data so tests/ can assert that they still
# produce the timelines the README, EXERCISES and TEXTBOOK describe.
#
# BARGE_IN_AT_MS is chosen to fall between the two architectures' first audio: the
# speech-to-speech agent is already talking and gets cut off, the pipeline is still
# thinking and never speaks at all. Run both modes and compare.
BARGE_IN_AT_MS = 1800


def dialogue_stream() -> list[Frame]:
    """Three turns, spaced so every reply finishes before the next turn starts."""
    return merge(
        utterance("hello there", start_ms=0),
        utterance("what is the weather today", start_ms=4000),
        utterance("tell me a joke", start_ms=9000),
    )


def barge_in_stream() -> list[Frame]:
    """One turn, interrupted partway through the agent's answer."""
    return merge(
        utterance("tell me a joke", start_ms=0),
        utterance("actually what time is it", start_ms=BARGE_IN_AT_MS),
    )


def run_stream(mode: str, frames: list[Frame]) -> None:
    for e in RealtimeSession(mode=mode).run(frames):
        print("  " + e.line())


def interactive(mode: str) -> None:
    print("Speak by typing a line (each line is one user turn). 'quit' to exit.\n")
    session = RealtimeSession(mode=mode)
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.lower() in ("quit", "exit"):
            break
        if not line:
            continue
        # Each typed line is one self-contained turn (no barge-in in this mode).
        for e in session.run(utterance(line)):
            if e.kind == "response_start":
                print(f"  agent> {e.text}   (first audio {e.latency_ms}ms after you stopped)")


def main() -> int:
    parser = argparse.ArgumentParser(description="A simulated realtime voice agent.")
    parser.add_argument("--mode", choices=["pipeline", "speech_to_speech"], default="pipeline")
    parser.add_argument("--demo", choices=["dialogue", "barge-in"], help="run a scripted demo instead of interactive")
    args = parser.parse_args()

    load_dotenv()
    ensure_ready()
    print(f"Provider: {describe()}   Mode: {args.mode}\n")

    if args.demo == "dialogue":
        print("Scripted clean dialogue (no interruptions):\n")
        run_stream(args.mode, dialogue_stream())
    elif args.demo == "barge-in":
        print("Scripted barge-in (user interrupts the agent mid-answer):\n")
        run_stream(args.mode, barge_in_stream())
    else:
        interactive(args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
