# Exercises: make the learning stick

Reading code teaches you less than *predicting* what it will do and then checking.
This file turns each section of the [README](README.md) into a few quick
active-recall prompts.

How to use it: work the section first, then come back. **Commit to an answer
before you run or reveal.** The prediction is where the learning happens. Answers
are hidden behind ▸ toggles.

> **Every section runs offline**: this whole dive is a deterministic simulator
> with no key and no cost.

---

## Section 2: Audio is a stream of frames

**Recall (`01`).** In realtime voice, why do you never just "upload the audio and
wait," and what does that force you to reason about that batch audio doesn't?

<details><summary>▸ Answer</summary>

Because there's no end to wait for. Audio streams continuously, in both directions
at once, and you only ever have the frames *so far*. That forces **turn detection**:
you have to decide, from silence, when the user is done talking. Too eager and you
cut them off; too patient and the agent feels slow. Batch audio never has to make
that call.
</details>

---

## Section 3: The pipeline

**Predict (`02`).** The STT→LLM→TTS pipeline has per-stage latencies of 300 / 500 /
200 ms, and the VAD waits 500 ms of silence before deciding the user is done.
What's the time-to-first-audio the user feels, and why isn't it the max of the
stages?

<details><summary>▸ Answer</summary>

1500 ms. The stages run **in series** (you can't synthesize speech until the LLM has
produced text until STT has produced a transcript), so their delays add rather than
overlap, and all three sit behind the 500 ms end-pointing wait, because nothing can
start until the agent concludes the turn is over. If you only counted the models you
would get 1000 ms and be wrong by a third. Streaming the stages so they overlap is
the main way to shrink the processing half; tightening the VAD window shrinks the
other half, at the cost of cutting people off mid-thought.
</details>

**Recall.** The pipeline is slower than one model, so why would anyone choose it?

<details><summary>▸ Answer</summary>

**Control and observability.** There's a text transcript in the middle you can log,
moderate, edit, hand to a tool or RAG, and audit, and you can swap any stage's
vendor independently. Speech-to-speech hides all of that.
</details>

---

## Section 4: The turn-taking state machine

**Recall (`03`).** Name the four states and the transition between each.

<details><summary>▸ Answer</summary>

LISTENING → (VAD sees the user stop) → THINKING → (first audio is ready) → SPEAKING
→ (response finishes) → LISTENING. And a fifth edge that section 5 adds: SPEAKING →
(user starts talking = barge-in) → LISTENING, cancelling the output.
</details>

---

## Section 5: Barge-in

**Predict (`04`).** The user asks for a joke; the agent starts answering at 2100 ms;
the user cuts in at 2400 ms. What does the session do, and what happens to the rest
of the joke?

<details><summary>▸ Answer</summary>

It fires a **barge-in**: the agent stops speaking, the rest of the planned joke is
discarded (never "played"), and the new speech is treated as the next turn. A good
voice agent yields the instant it hears you. An agent that finishes its sentence
over you feels broken.
</details>

**Recall.** What two things must be true for barge-in to work at all?

<details><summary>▸ Answer</summary>

**Full-duplex audio** (you're still *listening* while you speak, so you can even
detect the interruption) and **fast cancellation** (kill the TTS stream, flush the
playback buffer, and cancel the in-flight model response quickly enough to feel
instant). If you only listened between turns, you couldn't be interrupted.
</details>

---

## Section 6: The latency budget

**Predict (`05`).** Same turn, pipeline vs speech-to-speech, with processing budgets
of 1000 ms and 500 ms and a 500 ms end-pointing window. Which is faster to first
audio, and by how much? Careful: there are two defensible answers.

<details><summary>▸ Answer</summary>

Speech-to-speech, by **2× on processing** (500 ms vs 1000 ms) but only **1.5× on the
gap the user actually hears** (1000 ms vs 1500 ms), because both architectures wait
out the same 500 ms of end-pointing before either of them starts. The second number
is the honest one for a product decision, and the habit worth taking: a shared fixed
cost always compresses a ratio, so quote the improvement your user can perceive, not
the one your component benchmark shows. Latency is voice's make-or-break metric,
since humans notice a gap past ~300-500 ms, so that difference is felt directly.
</details>

---

## Section 7: Speech-to-speech

**Recall (`06`).** Speech-to-speech is faster and more natural. What does it cost
you, and when would you deliberately choose the slower pipeline instead?

<details><summary>▸ Answer</summary>

It costs **control and observability**: no transcript to log, moderate, redact,
or feed to a tool, and it's harder to steer. Choose the pipeline when you need that
transcript: guardrails/moderation, tool or RAG calls on the text, an auditable log,
or independent vendor choice per stage. Many production systems go hybrid:
speech-to-speech for the turn, a parallel transcript for safety.
</details>

---

## Capstone: `voice_agent.py`

**Do.** Run `python hands_on/voice_agent.py --demo barge-in` in both `--mode
pipeline` and `--mode speech_to_speech`. Does the interruption land at the same
point? Why not?

<details><summary>▸ Answer</summary>

No. The interruption arrives at the same moment (1800 ms) in both runs, but it lands
in a different state. Speech-to-speech began speaking at 1600 ms, so it is cut off
mid-joke and you see a `response_start` before the barge-in. The pipeline would not
have spoken until 2100 ms, so it is still in THINKING; the turn is superseded and
its planned reply is dropped without a sound ever coming out. Same interruption,
different code path, because latency changed *when* the agent was speaking.
</details>

**Stretch.** In interactive mode, ask the same question and compare the reported
time-to-first-audio across `--mode pipeline` and `--mode speech_to_speech`. When the
latency difference in the readout feels like the difference between a snappy and a
laggy assistant, the reason latency dominates voice has landed.

---

### Where to take it next

Wire the state machine in `voice/session.py` to a real transport: a speech-to-speech
API over WebSocket (OpenAI's Realtime API, Google's Gemini Live API), sending mic
frames and receiving audio frames. The turn-taking, barge-in, and latency logic you
built here is exactly what you drive with it; only the frames become real. If you'd
rather not write the plumbing, read Pipecat or LiveKit Agents instead: you'll
recognise every moving part, which is what building it from scratch bought you.
