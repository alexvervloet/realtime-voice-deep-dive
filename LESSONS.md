# Lessons

## A documented exercise asserted an outcome the code never produced

- **Expected:** the capstone's barge-in demo, run in both `--mode pipeline` and
  `--mode speech_to_speech`, would show the interruption landing in two different
  states. The README, EXERCISES.md and TEXTBOOK.md 12.4 all taught that contrast,
  and TEXTBOOK.md built a point on top of it: latency changes which code path runs.
- **Actual:** it never happened. The demo interrupted at 1800 ms, which is after
  *both* architectures had started speaking, so both took the identical mid-response
  branch. The claim had been written from reasoning about the model rather than from
  reading the output, and it stayed wrong through several documentation passes,
  because prose about a program is not checked by running the program.
- **Next time:** any millisecond figure that appears in prose has to come from a run,
  and a claim that two configurations differ has to be asserted somewhere a test can
  fail. `tests/test_session.py` now imports the capstone's own scripted streams
  rather than copies of them, so retiming a demo and leaving the docs behind breaks
  the build.

## The latency budget omitted the largest line in it

- **Expected:** time-to-first-audio for the pipeline was STT + LLM + TTS = 1000 ms,
  which is what every example, exercise answer, and README section quoted.
- **Actual:** the session started that clock at the user's last word, but nothing can
  begin until the VAD has waited out its silence window and concluded the turn is
  over. The real gap was 1500 ms, so the dive understated its own headline number by
  a third, while the chapter next door argued that a fifth of a second is felt.
  Worse, the omission flattered the comparison it was teaching: both architectures
  wait out the same window, so speech-to-speech is 1.5x faster on what a user hears,
  not the 2x the model latencies alone suggest.
- **Next time:** when a budget compares two designs, model the fixed costs they share
  before the ones that differ. A shared cost in front of the thing you optimised is
  the most common way an honest benchmark still misleads.

## An unused dependency described itself as load-bearing

- **Expected:** `rich` was in `requirements.txt` because the examples render their
  timelines with it, as both the requirements comment and `check_setup.py` said.
- **Actual:** nothing imported it. Every example printed with the standard library.
  The dependency pulled three transitive packages into a repo whose selling point is
  that it needs almost nothing, and two files vouched for a use that never existed.
- **Next time:** grep for the import before believing the comment. A setup checker
  that reports on a package should be checking something the code actually loads.
