"""
Tests for the simulator, and for the numbers the docs quote.

The docs are full of millisecond figures: the README's budget, the EXERCISES
answers, the prose at the bottom of each example. Those figures are only true if
the code still produces them, and nothing was checking. An earlier version of this
repo taught a barge-in exercise whose stated outcome the demo never produced (see
LESSONS.md), which is exactly what this file exists to prevent.

So: assert the timelines, and assert them with the same numbers that appear in
prose. If you change a latency constant, these fail and point at the docs to fix.

    python -m unittest discover
"""

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from voice import RealtimeSession, merge, segment, utterance
from voice.stages import (
    LLM_LATENCY_MS,
    S2S_LATENCY_MS,
    STT_LATENCY_MS,
    TTS_LATENCY_MS,
    VAD_SILENCE_MS,
)


def timeline(events):
    return [(e.t_ms, e.kind) for e in events]


def load_capstone():
    """Import hands_on/voice_agent.py by path (hands_on is not a package).

    The tests drive the capstone's own scripted streams rather than copies of them,
    so retiming a demo and forgetting the docs breaks the build."""
    spec = importlib.util.spec_from_file_location(
        "voice_agent", os.path.join(ROOT, "hands_on", "voice_agent.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capstone = load_capstone()


class TestFrames(unittest.TestCase):
    def test_utterance_frames_carry_their_duration(self):
        frames = utterance("what is the weather today", word_ms=150)
        speech = [f for f in frames if f.kind == "speech"]
        self.assertEqual(len(speech), 5)
        self.assertTrue(all(f.duration_ms == 150 for f in speech))

    def test_turn_ends_when_the_last_word_finishes(self):
        # Five words at 150ms starting at 0 occupy 0-750ms, not 0-600ms. Example 01
        # prints this span in prose.
        turn = segment(utterance("what is the weather today"), VAD_SILENCE_MS)[0]
        self.assertEqual((turn.start_ms, turn.end_ms), (0, 750))

    def test_merge_returns_frames_in_time_order(self):
        frames = merge(utterance("hello there"), utterance("what time is it", start_ms=4000))
        self.assertEqual([f.t_ms for f in frames], sorted(f.t_ms for f in frames))


class TestLatencyBudget(unittest.TestCase):
    """The figures quoted in README section 6 and EXERCISES section 3 and 6."""

    def test_pipeline_felt_gap_is_1500ms(self):
        self.assertEqual(VAD_SILENCE_MS + STT_LATENCY_MS + LLM_LATENCY_MS + TTS_LATENCY_MS, 1500)

    def test_speech_to_speech_felt_gap_is_1000ms(self):
        self.assertEqual(VAD_SILENCE_MS + S2S_LATENCY_MS, 1000)

    def test_reported_latency_includes_the_end_pointing_wait(self):
        for mode, expected in (("pipeline", 1500), ("speech_to_speech", 1000)):
            with self.subTest(mode=mode):
                events = RealtimeSession(mode=mode).run(utterance("what is the weather today"))
                start = next(e for e in events if e.kind == "response_start")
                self.assertEqual(start.latency_ms, expected)
                # The event's own timestamp has to agree with the latency it reports.
                end_of_turn = next(e for e in events if e.kind == "user_speech_end")
                self.assertEqual(start.t_ms - end_of_turn.t_ms, expected)

    def test_speech_to_speech_is_1_5x_faster_overall_and_2x_on_processing(self):
        pipe, s2s = 1500, 1000
        self.assertAlmostEqual(pipe / s2s, 1.5)
        self.assertAlmostEqual((pipe - VAD_SILENCE_MS) / (s2s - VAD_SILENCE_MS), 2.0)


class TestTurnTaking(unittest.TestCase):
    def test_clean_turn_cycles_without_interruption(self):
        events = RealtimeSession().run(utterance("what is the weather today"))
        self.assertEqual(
            timeline(events),
            [(0, "user_speech_start"), (750, "user_speech_end"),
             (2250, "response_start"), (3300, "response_end")],
        )

    def test_three_turn_dialogue_never_overlaps(self):
        # Example 03 promises a clean cycle per turn: no barge-in anywhere.
        events = RealtimeSession().run(capstone.dialogue_stream())
        self.assertNotIn("interrupted", [e.kind for e in events])
        self.assertEqual(len([e for e in events if e.kind == "response_end"]), 3)


class TestBargeIn(unittest.TestCase):
    def test_example_04_is_cut_off_mid_response(self):
        # Example 04's prose: the agent starts at 2100ms, the user cuts in at 2400ms.
        events = RealtimeSession().run(merge(
            utterance("tell me a joke", start_ms=0),
            utterance("actually what time is it", start_ms=2400),
        ))
        self.assertEqual(timeline(events)[:4], [
            (0, "user_speech_start"), (600, "user_speech_end"),
            (2100, "response_start"), (2400, "interrupted"),
        ])

    def test_capstone_demo_lands_in_a_different_state_per_architecture(self):
        """The exercise in README, EXERCISES and TEXTBOOK 12.4 rests on this.

        Same interruption at 1800ms: speech-to-speech is already talking and gets
        cut off, the pipeline has not spoken and is superseded."""
        def run(mode):
            return RealtimeSession(mode=mode).run(capstone.barge_in_stream())

        self.assertEqual(capstone.BARGE_IN_AT_MS, 1800)  # the figure EXERCISES quotes
        s2s = timeline(run("speech_to_speech"))
        self.assertIn((1600, "response_start"), s2s)
        self.assertIn((1800, "interrupted"), s2s)
        self.assertLess(s2s.index((1600, "response_start")), s2s.index((1800, "interrupted")))

        pipe = timeline(run("pipeline"))
        self.assertEqual(pipe[2], (1800, "interrupted"))
        spoke_before_the_interruption = [t for t, k in pipe if k == "response_start" and t <= 1800]
        self.assertEqual(spoke_before_the_interruption, [])

    def test_a_dropped_reply_says_so(self):
        events = RealtimeSession().run(capstone.barge_in_stream())
        interrupted = next(e for e in events if e.kind == "interrupted")
        self.assertIn("dropped", interrupted.text)


class TestEdgeCases(unittest.TestCase):
    def test_empty_and_silent_streams_produce_no_events(self):
        for name, frames in (("empty", []), ("silence only", utterance(""))):
            with self.subTest(stream=name):
                self.assertEqual(RealtimeSession().run(frames), [])

    def test_speech_with_no_trailing_silence_still_closes_the_turn(self):
        turns = segment(utterance("hello there", trailing_silence_ms=0), VAD_SILENCE_MS)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].words, ["hello", "there"])

    def test_speech_closer_together_than_the_vad_window_is_one_turn(self):
        turns = segment(merge(
            utterance("hello there"),
            utterance("what is the time", start_ms=400),
        ), VAD_SILENCE_MS)
        self.assertEqual(len(turns), 1)

    def test_an_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            RealtimeSession(mode="telepathy")


if __name__ == "__main__":
    unittest.main()
