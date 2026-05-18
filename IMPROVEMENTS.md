# Improvement Plan

Findings from a full audit of the codebase. Items are grouped by theme and ordered by priority within each group.

---

## 1. Broken / non-functional behaviour

These are bugs where the code exists but the expected outcome doesn't happen.

### 1.1 Web settings panel has no effect on the backend

**What's wrong:** `SettingsPanel` → `useEndpointConfig` → `POST /api/config` → `config.local.json` is a complete chain, but the Python backend never reads `config.local.json`. It loads `config.yaml` once at startup and never looks at it again. The README claim that "the backend polls `/api/config`" is incorrect.

**Fix options:**
- Add a polling loop in `app.py` (every N seconds, re-read `config.local.json`, reinitialise the LLM service if values changed).
- Alternatively, add a `/reload` HTTP endpoint and have the web UI POST to it after saving.

### 1.2 Docker compose networking is broken

**What's wrong:** The `voice-assistant` service sets `network_mode: host` but also sets `OLLAMA_HOST=http://ollama:11434`. In host-networking mode the Docker DNS service-name `ollama` doesn't resolve; the correct value would be `http://localhost:11434`.

**Fix:** Either remove `network_mode: host` and use the default bridge network (so the `ollama` hostname resolves), or change the env var to `http://localhost:11434` and document that both containers share the host network.

---

## 2. Missing features (stubs wired to nothing)

### 2.1 Transcript data never reaches the web UI

The `TranscriptPanel` component and the `TranscriptMessage` type are fully implemented but the panel always shows "Conversation will appear here…". In WebSocket mode the server sends raw PCM bytes only — no STT text, no LLM reply text, nothing.

**Fix:** Add a lightweight framing layer to the WebSocket protocol. For example, prefix binary audio frames with a header byte `0x01`, and send JSON text frames (`0x00` prefix or just plain JSON strings) for `{"type":"transcript","role":"user","text":"..."}` and `{"type":"transcript","role":"assistant","text":"..."}` messages. The web hook can demux them and call an `addMessage` callback.

### 2.2 Daily.co integration is a placeholder

`web/app/api/connect/route.ts` returns hardcoded mock values and `useVoiceConnection` is never used in the rendered UI. The `@daily-co/daily-js` and `@daily-co/daily-react` packages are installed and add bundle weight for no benefit.

**Options:**
- Implement it (requires Daily API keys, Pipecat Daily transport, room/token creation logic).
- Remove it: delete `useVoiceConnection.ts`, `web/app/api/connect/`, both Daily npm packages, and the `daily` Pipecat extra in `requirements.txt`.

If removing, do it cleanly so the codebase doesn't carry dead code.

### 2.3 No conversation context passed to the LLM

Each utterance is processed independently. The LLM has no memory of previous turns, so it can't answer follow-up questions or refer back to earlier statements.

**Fix:** Maintain a `messages: list[dict]` buffer per session (in the WebSocket handler and in `run_local`). Prepend the `system_prompt` as the first message, then append `{"role": "user", "content": text}` / `{"role": "assistant", "content": response}` pairs. Cap history to avoid exceeding the context window (a rolling window of the last N messages works well).

---

## 3. Code duplication

### 3.1 Service initialisation is copy-pasted between modes

`run_local()` and `WebSocketAudioServer.handle_client()` contain nearly identical blocks: STT init, LLM init, tool registration (all six `@llm.function` decorators), TTS init. Future changes (e.g. adding a seventh tool) require two edits.

**Fix:** Extract a `build_services(config)` factory that returns `(stt, llm, tts, tools_service)` with all function registrations applied. Both modes call this factory.

---

## 4. WebSocket mode is significantly weaker than local mode

### 4.1 No VAD in WebSocket mode

Local mode uses `SileroVADAnalyzer` to detect speech boundaries. WebSocket mode processes every 1-second chunk unconditionally — silence and background noise get transcribed, adding latency and spurious LLM calls.

**Fix:** Integrate Silero VAD server-side into the WebSocket audio loop. Buffer incoming audio, run VAD on each chunk, and only pass to STT when speech is detected. The `vad` section already exists in `config.yaml`.

### 4.2 Fixed 1-second chunking adds unnecessary latency

The current loop waits until `sample_rate * 2` bytes are buffered before processing. Short utterances still wait a full second before STT starts.

**Fix:** Run VAD on smaller sub-chunks (e.g. 256 ms) and trigger STT on end-of-speech rather than on a fixed timer.

---

## 5. Security

### 5.1 WebSocket server has no authentication

`WebSocketAudioServer` binds to `0.0.0.0:8765` with no token check. Any client on the network can connect, drive the LLM, and trigger n8n webhooks (smart home, messages, etc.).

**Fix:** Accept a shared secret via `config.yaml` (e.g. `server.secret_key`). On connection, expect the first message to be a JSON auth frame `{"token": "..."}`. Reject and close if it doesn't match.

The web UI should send this token on connect — it can be read from an env var (`NEXT_PUBLIC_WS_TOKEN`).

---

## 6. Browser API

### 6.1 ScriptProcessorNode is deprecated

`useVoiceChat.ts` uses `createScriptProcessor` (deprecated since 2018, runs on the main thread). The comment in the code acknowledges this.

**Fix:** Migrate to `AudioWorkletNode`. This requires a small `processor.worklet.js` file registered with `audioCtx.audioWorklet.addModule()`. The PCM conversion logic moves into the worklet. This improves real-time performance and future-proofs the code.

---

## 7. Error handling

### 7.1 Config save failure is silently swallowed

`useEndpointConfig.ts` wraps the `POST /api/config` call in `try/catch {}` with an empty catch. Users never know if their settings failed to persist.

### 7.2 Backend sends no error signal to browser client

If STT, LLM, or TTS throws during WebSocket processing, the exception is caught and logged server-side, but the WebSocket connection simply goes quiet. The browser has no way to distinguish "thinking" from "crashed".

**Fix for both:** Send a JSON error frame back to the client (same framing as transcript messages above), and surface it briefly in the UI.

---

## 8. Tests

There are no tests at all. The minimum useful baseline:

- **Python unit tests** (pytest): `FasterWhisperSTTService.run_stt` with a synthetic audio array, `N8nToolsService.execute_tool` with a mocked `aiohttp` session, `handle_function_call` argument parsing.
- **Frontend unit tests** (Jest + React Testing Library): `useEndpointConfig` save/load from localStorage, `TranscriptPanel` renders messages correctly.
- **Integration test**: WebSocket round-trip with a mocked STT/LLM/TTS (confirms the binary protocol and JSON framing are consistent).

---

## 9. Minor / housekeeping

- `app.py` imports `struct` but never uses it — remove.
- `requirements.txt` includes the `daily` Pipecat extra which is unused (see 2.2).
- The `models/` directory referenced in `docker-compose.yml` volumes doesn't exist in the repo and should be created or documented.
- Docker compose has no health checks; Ollama takes several seconds to be ready and `voice-assistant` may crash before the API is up. Add a `healthcheck` and `depends_on.condition: service_healthy`.
