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

from voice import RealtimeSession, describe, ensure_ready, merge, utterance


def run_stream(mode: str, frames) -> None:
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
            elif e.kind == "user_speech_end":
                pass  # we already have the text


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
        run_stream(args.mode, merge(
            utterance("hello there", start_ms=0),
            utterance("what is the weather today", start_ms=4000),
            utterance("tell me a joke", start_ms=9000),
        ))
    elif args.demo == "barge-in":
        print("Scripted barge-in (user interrupts the agent mid-answer):\n")
        run_stream(args.mode, merge(
            utterance("tell me a joke", start_ms=0),
            utterance("actually what time is it", start_ms=1700),
        ))
    else:
        interactive(args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
