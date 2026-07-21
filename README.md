# Realtime Voice: A Guided Deep Dive

A hands-on playground for the one whole category of AI product the rest of this
series can't prepare you to build: **realtime conversational voice.** You'll build
a from-scratch simulator of a realtime session and understand every moving part:
audio as a stream of frames, turn detection, the STT→LLM→TTS pipeline, the
turn-taking state machine, **barge-in** (interrupting the agent mid-sentence),
latency budgets, and the architectural fork between a pipeline and a single
speech-to-speech model. No framework magic, just enough code to see how a voice
agent actually keeps a conversation.

The honest twist that shapes this dive: a genuine realtime voice session needs
low-latency, full-duplex audio (a microphone, a speaker, a WebSocket or WebRTC
transport) that **can't** be shown honestly in a small, from-scratch, offline
example. So this repo is a **deterministic simulator**: audio is modeled as
timestamped frames and each stage carries a latency budget in milliseconds, so you
can watch turn-taking, barge-in, and the latency math play out exactly, offline,
with no key, for $0. The transport is the one thing the simulation stands in for;
the state machine, the architectures, and the reasoning are the real ones, and the
README maps each to production.

This is a **bonus dive**. It picks up exactly where
[Multimodal](https://github.com/alexvervloet/multimodal-deep-dive) stops. That dive
covers *batch* speech-to-text and text-to-speech and lists realtime as out of scope;
this is that scope. Its code depends on none of the others.

Like its siblings, it's meant to be *walked through*. Each section ends with
something to run, and **every section runs offline and free**.
[EXERCISES.md](EXERCISES.md) has a predict-then-run prompt for each one.

---

## 0. The one big idea

> **Realtime voice is a low-latency, full-duplex loop: audio streams in and out at
> once, the agent can be interrupted mid-sentence, and every hundred milliseconds
> is felt. The engineering is a turn-taking state machine over that stream, plus
> one architectural choice: an STT→LLM→TTS pipeline, or a single speech-to-speech
> model.**

That's the whole repo. Batch audio (the Multimodal dive) is "upload a file, wait,
get a result." Realtime is a *conversation*: you never have the whole recording,
the user can cut in at any moment, and a one-second pause feels broken. Everything
below: frames, turn detection, barge-in, the latency budget, the two architectures
is a facet of that one sentence. Hold onto it and none of this feels complicated.

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
#    (Wiring up a real realtime API? Its key goes in your OS keychain, not .env 
#     see ../SECRETS.md.)

# 4. Confirm everything is wired up (makes no API call, costs nothing)
python check_setup.py
```

There is **one provider here: `mock`**, and it needs no key. Unlike the sibling
repos, this dive doesn't switch between OpenAI and Claude. See the box below for
why. Everything runs offline and deterministically.

> **Why a simulator, not a real provider.** Realtime voice needs full-duplex
> audio I/O and a streaming transport; wiring that to a real API means a mic, a
> speaker, WebRTC/WebSocket plumbing, and platform-specific audio libraries, none
> of which belongs in a small, readable, offline teaching repo. So we simulate the
> *mechanics* (frames, latency, turn-taking, barge-in) exactly and deterministically.
> The state machine and architecture choices are real; only the transport is mocked.
> Production uses the **OpenAI Realtime API** (speech-to-speech over WebSocket/WebRTC)
> or a streaming STT/LLM/TTS pipeline, mapped in "From teaching code to production."

---

## 2. Audio is a stream of frames

```bash
python examples/01_audio_is_frames.py        # offline
```

The first mental shift: you never have "the recording." Audio arrives as a
continuous stream of tiny frames (~10–20 ms each), and you work with the frames so
far. The example builds one simulated utterance as frames (a speech frame per word,
then a run of silence) and a simple **voice-activity** rule finds the end of the
turn. Turn detection is a judgment call over silence: too eager and you cut the user
off; too patient and the agent feels slow. Everything else is built on this stream.
([voice/audio.py](voice/audio.py))

---

## 3. The pipeline: STT → LLM → TTS

```bash
python examples/02_pipeline.py
```

The first way to build a voice agent is three models in series: speech-to-text →
the LLM → text-to-speech. Each hop adds delay, and the number the user *feels* is
**time-to-first-audio**: how long after they stop talking before they hear
anything. For the pipeline that's STT + LLM + TTS, all stacked. The example prints
the budget so you see where the second of dead air comes from, and why streaming
each stage (so they overlap) is the fix. The pipeline's payoff is **control**:
there's a text transcript in the middle you can log, moderate, and edit.
([voice/stages.py](voice/stages.py))

---

## 4. The turn-taking state machine

```bash
python examples/03_turn_taking.py
```

A voice agent is a state machine over the stream: **LISTENING** → (user stops) →
**THINKING** → (first audio) → **SPEAKING** → (done) → **LISTENING**. The example
runs a clean, non-overlapping three-turn dialogue so you can watch the machine
cycle once per turn. Real conversations aren't this tidy, which is the next section.
([voice/session.py](voice/session.py))

---

## 5. Barge-in: the human interrupts

```bash
python examples/04_barge_in.py
```

This is the feature that separates a voice agent from a walkie-talkie. People
interrupt ("no wait, actually...") and a good agent **stops talking instantly**,
discards the rest of its planned audio, and listens. An agent that talks over you
feels broken, and it's the most common thing that ruins a voice demo. The example
sends a long agent response, has the user cut in partway through, and shows the
session fire a barge-in and re-enter LISTENING mid-sentence. It works because of
full-duplex audio (you're still *listening* while speaking) and fast cancellation
(kill the TTS stream and flush the buffer the instant the user's voice is detected).

---

## 6. The latency budget

```bash
python examples/05_latency_budget.py
```

Latency is voice's make-or-break metric: humans notice a gap past ~300–500 ms, and
past that the agent feels sluggish or gets talked over. The example measures
time-to-first-audio both ways on the same turn, the three-hop pipeline vs a single
speech-to-speech model, and shows speech-to-speech is meaningfully faster to first
sound because it collapses three hops into one. Engineer against the number your
users *feel*, not the one on a spec sheet.

---

## 7. Speech-to-speech, and when to choose it

```bash
python examples/06_speech_to_speech.py
```

Speech-to-speech uses a single multimodal model that hears audio and speaks audio
directly, with no transcript in the middle. It wins on **latency** (one hop) and
**naturalness** (it hears tone and pacing and can speak with them). It gives up
**control and observability**: there's no text step to log, moderate, redact, or
hand to a tool. The example lays out the decision: speech-to-speech for consumer
assistants and companions where latency and feel dominate; the pipeline when you
need the transcript for guardrails, tools/RAG, auditing, or per-stage vendor
choice; and often a hybrid (speech-to-speech turn + a parallel transcript for
safety). Same discipline as the whole series: pick the simplest architecture that
meets your real constraints.

---

## The capstone: `voice_agent.py`

Everything assembled into a simulated voice agent you can drive: interactive typed
turns, a latency readout per turn, a choice of architecture, and scripted demos of
a clean dialogue and a barge-in.

```bash
# Interactive: each line you type is one user turn (type 'quit' to exit)
python hands_on/voice_agent.py

# Choose the architecture:
python hands_on/voice_agent.py --mode speech_to_speech

# Scripted demos:
python hands_on/voice_agent.py --demo dialogue
python hands_on/voice_agent.py --demo barge-in
```

Read [hands_on/voice_agent.py](hands_on/voice_agent.py): it's just the library
(`RealtimeSession` + `utterance` + `merge`) wired to a CLI. **Suggested exercise:**
run `--demo barge-in` in both `--mode pipeline` and `--mode speech_to_speech` and
watch *when* the interruption lands change; a faster architecture is already
speaking (and gets cut off later) where the slower one is still thinking.

---

## Where to go next

You've built the mechanics of a realtime voice agent. The frontier is wiring them
to real audio and hardening the conversation:

- **A real transport**: the OpenAI Realtime API over WebSocket or WebRTC; send mic
  frames, receive audio frames, handle the session events. This dive's state machine
  is what you drive with it.
- **A real pipeline**: streaming STT (e.g. Whisper/Deepgram), a streaming LLM, and
  streaming TTS, with each stage overlapped so the latency stacks less.
- **Better turn detection**: a trained VAD / end-pointing model instead of a
  silence threshold, plus handling backchannels ("mm-hm") that *aren't* interruptions.
- **Tools & RAG in a voice loop**: let the agent call functions or retrieve
  ([RAG dive](https://github.com/alexvervloet/rag-deep-dive)) mid-conversation without
  killing latency, and speak a "let me check..." while it works.
- **Telephony**: SIP/PSTN integration, echo cancellation, and jitter buffers for
  real phone calls.
- **Emotion & prosody**: using and producing tone, not just words, the edge
  speech-to-speech models have.
- **Evaluating voice**: latency percentiles, interruption handling, and
  transcription accuracy as numbers you track ([Evals dive](https://github.com/alexvervloet/evals-deep-dive)).

---

## From teaching code to production

This repo simulates the transport so the mechanics are visible. Here's what each
piece becomes when it's real:

| This repo's simulation | In production |
|------------------------|---------------|
| Frames carry a word of text | **Real audio frames** (PCM, ~20 ms) over WebRTC/WebSocket, both directions at once |
| Per-stage latency is a fixed constant | **Measured, variable latency** (network + model + audio length) tracked as p50/p95 you engineer against |
| VAD is a silence threshold | A **trained VAD / end-pointing model**, tuned to not clip the user or wait too long, ignoring backchannels |
| Barge-in truncates a planned response | **Fast cancellation**: kill the TTS stream, flush the playback buffer, and cancel the in-flight model response the instant voice is detected |
| The mock "brain" is a keyword table | A **real LLM or speech-to-speech model**, streaming, possibly calling tools/RAG mid-turn |
| One turn = one typed line | **Continuous full-duplex audio** with echo cancellation, jitter buffering, and reconnection |
| No transcript stored | A **transcript + audio log** for QA, safety, and evals (and the moderation the Prompt Injection dive argues for) |

The general ops machinery (observability, cost, reliability, caching, guardrails,
eval gates) is built from scratch and wired into one running app in
**[Production](https://github.com/alexvervloet/ai-in-production-deep-dive)** (#8), which
runs offline on a mock provider.

---

## File map

```
check_setup.py              ← run first: verifies Python + packages (no key needed)
README.md                   ← this guide
EXERCISES.md                ← predict-then-run prompts, one per section
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
```

---

## Troubleshooting

Run `python check_setup.py` first. Then, by symptom:

| What you see | What it means / the fix |
|--------------|-------------------------|
| `ModuleNotFoundError` (rich / dotenv) | Deps aren't installed or the venv isn't active. `source .venv/bin/activate` then `pip install -r requirements.txt`. |
| "this dive is an offline simulator" note | You set `PROVIDER` to something other than `mock`. That's fine; there's only a mock here, and the note is just letting you know. |
| The timeline's millisecond numbers look arbitrary | They're teaching approximations (see `voice/stages.py`); the *shape* (more hops = more delay, barge-in cancels output) is the lesson, not the exact figures. |
| Barge-in didn't fire when I expected | The interrupting turn has to start *before* the agent's response ends. Move its `start_ms` earlier, or pick a longer reply. |
| `SyntaxError` / odd type errors on startup | You're likely on Python 3.9 or older; this repo needs 3.10+. |

Still stuck? Every file is small and self-contained. Open it, read the docstring at
the top, and run it directly. [voice/session.py](voice/session.py) is the whole
story: the turn-taking machine, with barge-in.

---

## The series

This is one of the standalone, hands-on deep dives into building with LLM APIs 
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

- [Agent Harnesses](https://github.com/alexvervloet/agent-harness-deep-dive): build on the loop: hooks, permissions, sandboxing, subagents
- [Context Engineering](https://github.com/alexvervloet/context-engineering-deep-dive): manage what's in the window
- [Multimodal](https://github.com/alexvervloet/multimodal-deep-dive): images & audio, not just text
- [Realtime Voice](https://github.com/alexvervloet/realtime-voice-deep-dive): low-latency speech-to-speech agents
- [Fine-tuning](https://github.com/alexvervloet/fine-tuning-deep-dive): teach a model new behavior by example
- [MCP](https://github.com/alexvervloet/mcp-deep-dive): serve tools, data & prompts over a standard protocol
- [Local Models](https://github.com/alexvervloet/local-models-deep-dive): run open-weight models on your own machine
- [Observability](https://github.com/alexvervloet/observability-deep-dive): watch a running app over time: drift, quality, alerting, the flywheel

**Realtime Voice is a bonus dive.** It slots right after
[Multimodal](https://github.com/alexvervloet/multimodal-deep-dive), since that dive does batch
speech-to-text and text-to-speech and marks realtime out of scope; this is that
scope.
