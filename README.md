# Realtime Voice: A Guided Deep Dive

A hands-on playground for the one category of AI product the rest of this series can't
prepare you to build: realtime conversational voice. You'll build a from-scratch simulator
of a realtime session and understand every moving part. Audio as a stream of frames, turn
detection, the STT then LLM then TTS pipeline, the turn-taking state machine, barge-in
(interrupting the agent mid-sentence), latency budgets, and the architectural fork between
a pipeline and a single speech-to-speech model. No framework magic, just enough code to see
how a voice agent actually keeps a conversation going.

One honest constraint shapes this dive. A genuine realtime voice session needs
low-latency, full-duplex audio, meaning a microphone, a speaker, and a WebSocket or WebRTC
transport, and none of that can be shown honestly in a small, from-scratch, offline
example. So this repo is a deterministic simulator. Audio is modeled as timestamped frames
and each stage carries a latency budget in milliseconds, so you can watch turn-taking,
barge-in, and the latency math play out exactly, offline, with no key, for $0. The
transport is the one thing the simulation stands in for. The state machine, the
architectures, and the reasoning are the real ones, and the README maps each to
production.

This is a bonus dive. It picks up exactly where
[Multimodal](https://github.com/alexvervloet/multimodal-deep-dive) stops. That dive covers
batch speech-to-text and text-to-speech and lists realtime as out of scope. This is that
scope. Its code depends on none of the others.

Like its siblings, walk through it. Each section ends with something to run, and every
section runs offline and free.
[EXERCISES.md](EXERCISES.md) has a predict-then-run prompt for each one, and
[TEXTBOOK.md](TEXTBOOK.md) is the lecture behind this lab: Chapter 12 of the
[AI Engineering Textbook](https://github.com/alexvervloet/ai-engineering-deep-dive),
on why conversational time is a harder constraint than machine time.

---

## 0. The one big idea

> **Realtime voice is a low-latency, full-duplex loop. Audio streams in and out at once,
> the agent can be interrupted mid-sentence, and every hundred milliseconds gets felt. The
> engineering is a turn-taking state machine over that stream, plus one architectural
> choice: an STT-LLM-TTS pipeline, or a single speech-to-speech model.**

That is the whole repo. Batch audio, from the Multimodal dive, is upload a file, wait, get
a result. Realtime is a conversation. You never have the whole recording, the user can cut
in at any moment, and a one-second pause feels broken. Everything below, from frames and
turn detection to barge-in, the latency budget, and the two architectures, is one face of
that sentence. Hold onto it and none of this feels complicated.

---

## 1. Setup (5 minutes)

```bash
# 1. Create an isolated Python environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies (tiny: the repo is an offline simulator)
pip install -r requirements.txt

# 3. Copy the env file: this dive is a fully offline simulator (no key needed)
cp .env.example .env
#    (Wiring up a real realtime API? Its key goes in your OS keychain, not .env.
#     See SECRETS.md in the series repo: https://github.com/alexvervloet/ai-engineering-deep-dive)

# 4. Confirm everything is wired up (makes no API call, costs nothing)
python check_setup.py
```

There is one provider here, `mock`, and it needs no key. Unlike the sibling repos, this
dive doesn't switch between OpenAI and Claude. The box below says why. Everything runs
offline and deterministically.

> **Why a simulator rather than a real provider.** Realtime voice needs full-duplex audio
> I/O and a streaming transport. Wiring that to a real API means a mic, a speaker, WebRTC
> or WebSocket plumbing, and platform-specific audio libraries, none of which belongs in a
> small, readable, offline teaching repo. So we simulate the mechanics, meaning frames,
> latency, turn-taking, and barge-in, exactly and deterministically. The state machine and
> the architecture choices are real. Only the transport is mocked. Production uses a
> speech-to-speech API over WebSocket or WebRTC, with OpenAI's Realtime API and Google's
> Gemini Live API the two obvious ones, or a streaming STT, LLM, and TTS pipeline, both
> mapped in "From teaching code to production."

---

## 2. Audio is a stream of frames

```bash
python examples/01_audio_is_frames.py        # offline
```

Here is the first mental shift. You never have the recording. Audio arrives as a continuous
stream of tiny frames, about 10 to 20 ms each, and you work with the frames so far. The
example builds one simulated utterance as frames, a speech frame per word followed by a run
of silence, and a simple voice-activity rule finds the end of the turn. Turn detection is a
judgment call over silence. Too eager and you cut the user off. Too patient and the agent
feels slow. Everything else is built on this stream. ([voice/audio.py](voice/audio.py))

---

## 3. The pipeline, STT then LLM then TTS

```bash
python examples/02_pipeline.py
```

The first way to build a voice agent is three models in series: speech-to-text, then the
LLM, then text-to-speech. Each hop adds delay, and the number the user feels is
time-to-first-audio, meaning how long after they stop talking before they hear anything.
That is the end-pointing wait first, because nothing downstream starts until the VAD
decides the user is done, then STT plus LLM plus TTS stacked on top. 1500 ms in this
repo's budget. The example prints it line by line so you see where the dead air comes from,
and why streaming each stage so they overlap is the fix. What the pipeline buys you is
control. There is a text transcript in the middle you can log, moderate, and edit.
([voice/stages.py](voice/stages.py))

---

## 4. The turn-taking state machine

```bash
python examples/03_turn_taking.py
```

A voice agent is a state machine over the stream. LISTENING, then the user stops, then
THINKING, then first audio, then SPEAKING, then done, then LISTENING again. The example
runs a clean, non-overlapping three-turn dialogue so you can watch the machine cycle once
per turn. Real conversations aren't this tidy, which is the next section.
([voice/session.py](voice/session.py))

---

## 5. Barge-in, where the human interrupts

```bash
python examples/04_barge_in.py
```

This is the feature that separates a voice agent from a walkie-talkie. People interrupt
("no wait, actually...") and a good agent stops talking on the spot, discards the rest of
its planned audio, and listens. An agent that talks over you feels broken, and it is the
most common thing that ruins a voice demo. The example sends a long agent response, has the
user cut in partway through, and shows the session fire a barge-in and re-enter LISTENING
mid-sentence. It works because of full-duplex audio, since you are still listening while
speaking, and fast cancellation, killing the TTS stream and flushing the buffer the instant
the user's voice is detected.

---

## 6. The latency budget

```bash
python examples/05_latency_budget.py
```

Latency is voice's make-or-break metric. Humans notice a gap past about 300 to 500 ms, and
past that the agent feels sluggish or gets talked over. The example splits
time-to-first-audio into end-pointing, processing, and the felt total, both ways on the
same turn. Speech-to-speech is 2× faster on the processing it controls and only 1.5× faster
overall, 1000 ms against 1500 ms, because both designs wait out the same silence window
before either of them starts. That third column is the honest one. Engineer against the
number your users feel rather than the one on a spec sheet, and remember that the biggest
single line in the budget is usually a threshold you chose, not a model you bought.

---

## 7. Speech-to-speech, and when to choose it

```bash
python examples/06_speech_to_speech.py
```

Speech-to-speech uses a single multimodal model that hears audio and speaks audio directly,
with no transcript in the middle. It wins on latency, since there is one hop, and on
naturalness, since it hears tone and pacing and can speak with them. It gives up control
and observability, because there is no text step to log, moderate, redact, or hand to a
tool. The example lays out the decision. Speech-to-speech for consumer assistants and
companions where latency and feel dominate. The pipeline when you need the transcript for
guardrails, tools and RAG, auditing, or per-stage vendor choice. And often a hybrid, with a
speech-to-speech turn plus a parallel transcript for safety. Same discipline as the whole
series. Pick the simplest architecture that meets your real constraints.

---

## The capstone: `voice_agent.py`

Everything assembled into a simulated voice agent you can drive. Interactive typed turns, a
latency readout per turn, a choice of architecture, and scripted demos of a clean dialogue
and a barge-in.

```bash
# Interactive: each line you type is one user turn (type 'quit' to exit)
python hands_on/voice_agent.py

# Choose the architecture:
python hands_on/voice_agent.py --mode speech_to_speech

# Scripted demos:
python hands_on/voice_agent.py --demo dialogue
python hands_on/voice_agent.py --demo barge-in
```

Read [hands_on/voice_agent.py](hands_on/voice_agent.py). It's the library,
`RealtimeSession` plus `utterance` plus `merge`, wired to a CLI. **Suggested exercise:** run
`--demo barge-in` in both `--mode pipeline` and `--mode speech_to_speech`. The interruption
arrives at the same moment in both and lands in a different state. Speech-to-speech is
already telling the joke and gets cut off mid-sentence, while the pipeline is still
thinking and never says a word. Latency changes how the agent feels and it also changes
which code path runs.

---

## Where to go next

You've built the mechanics of a realtime voice agent. What comes next is wiring them to
real audio and hardening the conversation.

- **A real transport.** A speech-to-speech API over WebSocket or WebRTC (OpenAI's
  Realtime API, Google's Gemini Live API). Send mic frames, receive audio frames, and
  handle the session events. This dive's state machine is what you drive with it.
- **A real pipeline.** A streaming STT model (batch Whisper is the wrong tool here,
  so reach for a realtime transcription endpoint or a vendor built for it, like
  Deepgram or AssemblyAI), a streaming LLM, and a streaming TTS vendor, with each
  stage overlapped so the latency stacks less.
- **Not writing the plumbing yourself.** Pipecat and LiveKit Agents are the
  open-source orchestrators most teams reach for. They own the transport, the VAD,
  and the interruption handling. Read one after this dive and you'll recognise every
  moving part, which is the point of building it from scratch first.
- **Better turn detection.** A trained VAD or end-pointing model instead of a silence
  threshold, plus handling backchannels ("mm-hm") that aren't interruptions.
- **Tools and RAG in a voice loop.** Let the agent call functions or retrieve
  ([RAG dive](https://github.com/alexvervloet/rag-deep-dive)) mid-conversation without
  killing latency, and speak a "let me check..." while it works.
- **Telephony.** SIP/PSTN integration, echo cancellation, and jitter buffers for
  real phone calls.
- **Emotion and prosody.** Using and producing tone as well as words, which is the edge
  speech-to-speech models have.
- **Evaluating voice.** Latency percentiles, interruption handling, and
  transcription accuracy as numbers you track ([Evals dive](https://github.com/alexvervloet/evals-deep-dive)).

---

## From teaching code to production

This repo simulates the transport so the mechanics stay visible. Here is what each piece
becomes when it's real.

| This repo's simulation | In production |
|------------------------|---------------|
| Frames carry a word of text | **Real audio frames** (PCM, ~20 ms) over WebRTC/WebSocket, both directions at once |
| Per-stage latency is a fixed constant | **Measured, variable latency** (network + model + audio length) tracked as p50/p95 you engineer against |
| VAD is a silence threshold | A **trained VAD / end-pointing model**, tuned to not clip the user or wait too long, ignoring backchannels |
| Barge-in truncates a planned response | **Fast cancellation**: kill the TTS stream, flush the playback buffer, and cancel the in-flight model response the instant voice is detected |
| The mock "brain" is a keyword table | A **real LLM or speech-to-speech model**, streaming, possibly calling tools/RAG mid-turn |
| One turn = one typed line | **Continuous full-duplex audio** with echo cancellation, jitter buffering, and reconnection |
| No transcript stored | A **transcript + audio log** for QA, safety, and evals (and the moderation the Prompt Injection dive argues for) |

The general ops machinery (observability, cost, reliability, caching, guardrails, eval
gates) gets built from scratch and wired into one running app in
[Production](https://github.com/alexvervloet/ai-in-production-deep-dive), #8, which runs
offline on a mock provider.

---

## File map

```
check_setup.py              ← run first: verifies Python + packages (no key needed)
README.md                   ← this guide (the lab)
TEXTBOOK.md                 ← Chapter 12: the lecture behind the lab
EXERCISES.md                ← predict-then-run prompts, one per section
LESSONS.md                  ← what this repo got wrong, and how it was caught
voice/                      ← the from-scratch simulator (read it!)
  audio.py                  ← audio as a stream of timestamped frames (+ builders)
  stages.py                 ← the two architectures as latency-annotated stages
  session.py                ← the turn-taking state machine (VAD turn detection + barge-in)
  providers.py              ← the mock-only provider shim (parity with the series)
hands_on/
  voice_agent.py            ← capstone: a simulated voice agent (interactive + demos)
examples/
  01_audio_is_frames.py     ← audio is a stream of frames; VAD finds the turn end
  02_pipeline.py            ← STT→LLM→TTS and its latency budget
  03_turn_taking.py         ← the LISTENING→THINKING→SPEAKING state machine
  04_barge_in.py            ← the user interrupts; the agent yields instantly
  05_latency_budget.py      ← time-to-first-audio: pipeline vs speech-to-speech
  06_speech_to_speech.py    ← one model; when to pick it over the pipeline
tests/
  test_session.py           ← locks the timelines the docs quote
```

---

## Troubleshooting

Run `python check_setup.py` first. Then, by symptom:

| What you see | What it means / the fix |
|--------------|-------------------------|
| `ModuleNotFoundError` (dotenv) | Deps aren't installed or the venv isn't active. `source .venv/bin/activate` then `pip install -r requirements.txt`. |
| "this dive is an offline simulator" note | You set `PROVIDER` to something other than `mock`. That's fine; there's only a mock here, and the note is just letting you know. |
| The timeline's millisecond numbers look arbitrary | They're teaching approximations (see `voice/stages.py`); the *shape* (end-pointing first, then hops that stack, and barge-in cancelling output) is the lesson, not the exact figures. |
| Barge-in didn't fire when I expected | The interrupting turn has to start *before* the agent's response ends. Move its `start_ms` earlier, or pick a longer reply. If it starts before the response *begins*, you get the other branch instead: the planned reply is dropped before a sound comes out. |
| `SyntaxError` / odd type errors on startup | You're likely on Python 3.9 or older; this repo needs 3.10+. |

Still stuck? Every file is small and self-contained. Open it, read the docstring at
the top, and run it directly. [voice/session.py](voice/session.py) is the whole
story: the turn-taking machine, with barge-in.

---

## The series

This is one of the standalone, hands-on deep dives into building with LLM APIs:
eight core, plus the bonus dives. Each stands on its own, with its own setup, examples,
and capstone, and they share one house style: provider-agnostic where it makes
sense, built from scratch (no frameworks), offline-first examples, and a real
capstone. Do them in any order; this sequence builds naturally:

1. [OpenAI API](https://github.com/alexvervloet/openai-api-deep-dive): the API from zero
2. [Claude API](https://github.com/alexvervloet/claude-api-deep-dive): the same ideas, the Anthropic way
3. [Prompt Engineering](https://github.com/alexvervloet/prompt-engineering-deep-dive): shape model behavior with better prompts
4. [RAG](https://github.com/alexvervloet/rag-deep-dive): answer questions over your own documents
5. [Evals](https://github.com/alexvervloet/evals-deep-dive): measure whether a change actually helps
6. [Agents](https://github.com/alexvervloet/agents-deep-dive): give a model tools and a loop so it can act
7. [Prompt Injection & Guardrails](https://github.com/alexvervloet/prompt-injection-deep-dive): attack and defend all of the above
8. [Production](https://github.com/alexvervloet/ai-in-production-deep-dive): operate one app end to end

**Bonus dives**, standalone and slotting in where they're most useful:

- [Agent Harnesses](https://github.com/alexvervloet/agent-harness-deep-dive): build on the loop, adding hooks, permissions, sandboxing, and subagents
- [Context Engineering](https://github.com/alexvervloet/context-engineering-deep-dive): manage what's in the window
- [AI Data Engineering](https://github.com/alexvervloet/ai-data-engineering-deep-dive): the corpus behind the index, with versions, lineage, ACLs, and deletes
- [Multimodal](https://github.com/alexvervloet/multimodal-deep-dive): images and audio as well as text
- [Realtime Voice](https://github.com/alexvervloet/realtime-voice-deep-dive): low-latency speech-to-speech agents
- [Fine-tuning](https://github.com/alexvervloet/fine-tuning-deep-dive): teach a model new behavior by example
- [MCP](https://github.com/alexvervloet/mcp-deep-dive): serve tools, data, and prompts over a standard protocol
- [Local Models](https://github.com/alexvervloet/local-models-deep-dive): run open-weight models on your own machine
- [Observability](https://github.com/alexvervloet/observability-deep-dive): watch a running app over time, covering drift, quality, alerting, and the feedback loop
- [Architecture](https://github.com/alexvervloet/architecture-deep-dive): the seams between the components, each decision measured rather than asserted
- [GenAI Security](https://github.com/alexvervloet/genai-security-deep-dive): treat the model as an untrusted principal, and put identity, supply chain, isolation, budgets, and release gates around it
- [Inference Platform Engineering](https://github.com/alexvervloet/inference-platform-deep-dive): turn finite GPU memory and a request queue into latency, throughput, and a fleet size you can defend
- [Testing & Delivery](https://github.com/alexvervloet/testing-and-delivery-deep-dive): decide whether a build is fit to promote, using evidence, gates, staged rollout, and rollback
- [Professional Tools](https://github.com/alexvervloet/professional-tools-deep-dive): rebuild each hand-written piece with the tool professionals reach for, and measure both

And the whole series lands in one codebase in the
[capstone](https://github.com/alexvervloet/deep-dive-capstone): a codebase Q&A tool
built step by step, one tag per dive.

**Realtime Voice is a bonus dive.** It slots right after
[Multimodal](https://github.com/alexvervloet/multimodal-deep-dive), since that dive does batch
speech-to-text and text-to-speech and marks realtime out of scope; this is that
scope.
