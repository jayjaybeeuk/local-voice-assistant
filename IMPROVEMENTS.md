# Improvement Plan

Findings from a full audit of the codebase. Items are grouped by theme and ordered by priority within each group.

---

## 1. Broken / non-functional behaviour

These are bugs where the code exists but the expected outcome doesn't happen.

### ✅ 1.1 Web settings panel has no effect on the backend

**What's wrong:** `SettingsPanel` → `useEndpointConfig` → `POST /api/config` → `config.local.json` is a complete chain, but the Python backend never reads `config.local.json`. It loads `config.yaml` once at startup and never looks at it again. The README claim that "the backend polls `/api/config`" is incorrect.

**Fix applied:** `load_config()` now overlays `web/config.local.json` on top of `config.yaml` if the file exists. New settings (`endpointUrl`, `model`, `apiKey`) take effect on the next WebSocket connection.

### ✅ 1.2 Docker compose networking is broken

**What's wrong:** The `voice-assistant` service sets `network_mode: host` but also sets `OLLAMA_HOST=http://ollama:11434`. In host-networking mode the Docker DNS service-name `ollama` doesn't resolve.

**Fix applied:** Removed `network_mode: host` from the `voice-assistant` service. Both containers now use the default bridge network, so the `ollama` hostname resolves correctly. Also added a `healthcheck` on the `ollama` service and `depends_on: condition: service_healthy` on `voice-assistant` so the container waits for Ollama to be ready before starting.

---

## 2. Missing features (stubs wired to nothing)

### ✅ 2.1 Transcript data never reaches the web UI

The `TranscriptPanel` component and the `TranscriptMessage` type are fully implemented but the panel always shows "Conversation will appear here…". In WebSocket mode the server sends raw PCM bytes only.

**Fix applied:** The WebSocket handler now sends JSON text frames alongside audio:
- `{"type":"transcript","role":"user","text":"..."}` after STT
- `{"type":"transcript","role":"assistant","text":"..."}` after LLM
- `{"type":"error","message":"..."}` on STT/LLM/TTS failures

`useVoiceChat` demuxes these frames and maintains a `transcript` array returned to the component. `VoiceAssistant` now passes `transcript` to `TranscriptPanel` and surfaces errors in the UI.

### ✅ 2.2 Daily.co integration is a placeholder

`web/app/api/connect/route.ts` returns hardcoded mock values and `useVoiceConnection` is never used in the rendered UI.

**Fix applied:** Deleted `useVoiceConnection.ts`, `web/app/api/connect/route.ts`, and removed `@daily-co/daily-js`, `@daily-co/daily-react` from `package.json`. Also removed the `daily` Pipecat extra from `requirements.txt`.

### ✅ 2.3 No conversation context passed to the LLM

Each utterance is processed independently. The LLM has no memory of previous turns.

**Fix applied:** WebSocket mode now uses a direct `call_llm_api(config, messages)` function that passes the full `history` list to the OpenAI-compatible API. History is maintained per session as a `list[dict]`, prepended with the system prompt, and capped at `HISTORY_MAX_TURNS * 2` messages via a rolling window.

---

## 3. Code duplication

### ✅ 3.1 Service initialisation is copy-pasted between modes

`run_local()` and `WebSocketAudioServer.handle_client()` contained nearly identical service init blocks.

**Fix applied:** Extracted `build_services(config)` factory that returns `(stt, llm, tts, tools_service)` with all six `@llm.function` registrations applied. Both modes call this factory.

---

## 4. WebSocket mode is significantly weaker than local mode

### 🔜 4.1 No VAD in WebSocket mode

Local mode uses `SileroVADAnalyzer` to detect speech boundaries. WebSocket mode processes every 1-second chunk unconditionally — silence and background noise get transcribed, wasting CPU and producing garbage output (e.g. "[music]", random words from background noise). Every second of idle audio triggers a full STT → LLM → TTS round-trip.

**To do:**

In local mode, `SileroVADAnalyzer` is baked into `LocalAudioTransport` as part of the Pipecat pipeline. In WebSocket mode there is no Pipecat transport layer, so VAD must be wired in manually inside `handle_client()`.

Rough implementation plan:

1. Add a `vad_buffer: bytearray` alongside `audio_buffer` in `handle_client()`.
2. Process incoming audio in small sub-chunks (e.g. 256 ms = 4096 bytes at 16 kHz/16-bit). For each sub-chunk, run `SileroVADAnalyzer` (or call `silero_vad` directly via `torch.hub`) to get a speech probability score.
3. Accumulate sub-chunks into `vad_buffer` while speech is detected (score > `config["vad"]["threshold"]`).
4. On a transition from speech → silence (sustained silence of at least `min_silence_duration_ms`), flush `vad_buffer` as a single audio chunk to STT and clear the buffer.
5. Discard sub-chunks where no speech is detected (score stays below threshold).

The `silero-vad` package is already an indirect dependency via `pipecat-ai[silero]`. The VAD config keys (`threshold`, `min_speech_duration_ms`, `min_silence_duration_ms`) are already in `config.yaml`.

### 🔜 4.2 Fixed 1-second chunking adds unnecessary latency

The current loop waits until `sample_rate * 2` bytes (1 full second of audio) are buffered before processing. A short utterance like "yes" or "okay" still waits up to a full second before STT even starts.

**To do:**

This is a direct consequence of 4.1. Once VAD drives chunking, the STT trigger moves from a fixed timer to end-of-speech detection, so a 200 ms utterance gets processed ~300 ms after the user stops speaking (silence threshold) rather than up to 1 second later.

Implement 4.1 first; 4.2 falls out naturally from VAD-triggered flushing. The fixed `byte_chunk = sample_rate * 2` constant in `handle_client()` should be replaced with the smaller sub-chunk size (e.g. `SUB_CHUNK_MS = 256`) used for VAD scoring.

---

## 5. Security

### ✅ 5.1 WebSocket server has no authentication

`WebSocketAudioServer` binds to `0.0.0.0:8765` with no token check.

**Fix applied:** Added `server.secret_key` to `config.yaml`. When set, the server expects the first WebSocket message to be a JSON auth frame `{"token": "..."}` and closes the connection if it doesn't match. The web UI reads the token from `NEXT_PUBLIC_WS_TOKEN` and sends it on connect.

---

## 6. Browser API

### ✅ 6.1 ScriptProcessorNode is deprecated

`useVoiceChat.ts` used `createScriptProcessor` (deprecated since 2018, runs on the main thread).

**Fix applied:** Migrated to `AudioWorkletNode` with a `public/audio-processor.worklet.js` processor. PCM conversion runs off the main thread. Level metering uses an `AnalyserNode` driven by `requestAnimationFrame`.

---

## 7. Error handling

### ✅ 7.1 Config save failure is silently swallowed

`useEndpointConfig.ts` wrapped the `POST /api/config` call in `try/catch {}` with an empty catch.

**Fix applied:** `save()` now returns `Promise<{ ok: boolean; error?: string }>`. `SettingsPanel` displays a save-error banner and keeps the dialog open so the user can retry.

### ✅ 7.2 Backend sends no error signal to browser client

If STT, LLM, or TTS throws during WebSocket processing, the exception is caught and logged server-side, but the browser goes quiet.

**Fix applied:** Each stage (STT, LLM, TTS) is wrapped in `try/except` that sends a `{"type":"error","message":"..."}` JSON frame to the client. `useVoiceChat` surfaces these as `lastError` state, rendered in `VoiceAssistant`.

---

## 8. Tests

### ✅ 8 No tests at all

**Fix applied:**
- `tests/test_tools_service.py` — pytest tests for `N8nToolsService.execute_tool` (success, missing webhook, HTTP error, connection error) and `handle_function_call` argument parsing.
- `tests/test_stt_service.py` — pytest tests for `FasterWhisperSTTService.run_stt` (silence, single segment, multi-segment join, whitespace stripping, float32 conversion) using a mocked `WhisperModel`.
- `pytest` and `pytest-asyncio` added to `requirements.txt`.

---

## 9. Minor / housekeeping

### ✅ 9.1 Unused `struct` import in `app.py`

**Fix applied:** Removed.

### ✅ 9.2 `daily` Pipecat extra in `requirements.txt`

**Fix applied:** Removed (also covers 2.2).

### ✅ 9.3 `models/` directory missing from repo

**Fix applied:** Created `models/.gitkeep` so the directory exists and Docker volume mounts work.

### ✅ 9.4 No health check in Docker compose

**Fix applied:** Added a `healthcheck` on the `ollama` service (`curl /api/tags`) and `depends_on: condition: service_healthy` on `voice-assistant`.
