# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python backend

```bash
# Install dependencies (requires PortAudio system package)
pip install -r requirements.txt

# Pre-download models (faster-whisper + Kokoro auto-download on first run otherwise)
python scripts/download_models.py

# Run in local audio mode (microphone → speaker)
python app.py

# Run in WebSocket mode (for web UI)
python app.py --ws
```

### Web UI (Next.js 14, lives in `web/`)

```bash
cd web
npm install
npm run dev      # dev server at http://localhost:3000
npm run build
npm run lint
```

### Docker

```bash
# Start Ollama only
docker compose up -d ollama

# Pull the LLM model
docker exec ollama ollama pull qwen3:8b

# Full stack (Ollama + voice assistant)
docker compose up
```

## Architecture

The system is a real-time voice pipeline built on [Pipecat](https://github.com/pipecat-ai/pipecat):

```
Microphone → VAD (Silero) → STT (faster-whisper) → LLM (Qwen3 via Ollama) → TTS (Kokoro) → Speaker
```

**Two run modes** share the same service layer but differ in transport:

- **Local mode** (`python app.py`): Uses `LocalAudioTransport` with a proper Pipecat `Pipeline` → `PipelineTask` → `PipelineRunner` chain. VAD runs inside the transport.
- **WebSocket mode** (`python app.py --ws`): `WebSocketAudioServer` manually bridges browser audio. The browser sends raw int16 PCM at 16 kHz; the server processes 1-second chunks through STT → LLM → TTS and returns raw int16 PCM audio.

**Services** (`services/`) are thin Pipecat subclasses with lazy model loading (via `_ensure_model()`):

- `FasterWhisperSTTService` — wraps `faster_whisper.WhisperModel`; falls back to CPU if CUDA init fails.
- `KokoroTTSService` — wraps `kokoro.KPipeline`; outputs float32 converted to int16 bytes.
- `N8nToolsService` — maps LLM function calls to n8n webhook POSTs. Tool definitions are the OpenAI function-calling format in `TOOL_DEFINITIONS`. n8n workflows must return `{"result": "..."}`.

**LLM function calling** is registered at startup using Pipecat's `@llm.function()` decorator pattern. All six tool names (`control_smart_home`, `query_calendar`, `send_message`, `add_to_list`, `web_search`, `set_reminder`) share a single handler that delegates to `N8nToolsService.execute_tool()`.

**Web UI** (`web/`) is Next.js 14 with Tailwind. The active audio path is `useVoiceChat` → raw WebSocket (ws://localhost:8765) → Python backend. Audio is captured via `ScriptProcessorNode`, converted float32→int16, sent as binary WebSocket frames, and played back using the Web Audio API with a sequential queue.

`useVoiceConnection` and `web/app/api/connect/route.ts` are stubs for a Daily.co integration that is not yet functional — `VoiceAssistant.tsx` uses `useVoiceChat`, not `useVoiceConnection`.

**Endpoint config** in the web UI flows: Settings panel → `localStorage` → `POST /api/config` → `web/config.local.json`. The Python backend does not poll this file; it reads `config.yaml` at startup only.

## Configuration

`config.yaml` is the single source of truth for the Python backend. Key values:

- `llm.base_url` — any OpenAI-compatible endpoint (default: Ollama at `http://localhost:11434/v1`)
- `stt.device` — `"auto"` resolves to `"cuda"` in code; falls back to CPU on failure
- `audio.sample_rate` — input sample rate (16000 Hz); `tts.sample_rate` is separate (24000 Hz)
- `n8n.webhooks` — map of tool name → webhook path; omitting a tool here means calls to it return an error string

## Audio format

All PCM audio throughout the pipeline is **16-bit signed integers, mono**. Input sample rate is 16000 Hz; TTS output is 24000 Hz. The WebSocket transport uses the input rate for both send and playback (`SAMPLE_RATE = 16000` in `useVoiceChat.ts`).

## Adding a new tool

1. Add an OpenAI function definition to `TOOL_DEFINITIONS` in `services/tools_service.py`.
2. Add the corresponding webhook path to `config.yaml` under `n8n.webhooks`.
3. Register the function name in both `run_local()` and `WebSocketAudioServer.handle_client()` in `app.py` with `@llm.function("your_tool_name")`.
4. Create the matching n8n workflow returning `{"result": "..."}`.
