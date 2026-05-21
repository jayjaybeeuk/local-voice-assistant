# Local Voice Assistant

A fully local, real-time voice conversation system using [Pipecat](https://github.com/pipecat-ai/pipecat) for pipeline orchestration.

## Architecture

```
┌─────────────┐    ┌─────┐    ┌────────────────┐    ┌──────────────────┐    ┌───────────┐    ┌──────────────┐
│ Microphone  │───▶│ VAD │───▶│ faster-whisper │───▶│ LLM              │───▶│ Kokoro TTS│───▶│   Speaker    │
│   Input     │    │     │    │     (STT)       │    │ (any OpenAI API) │    │           │    │   Output     │
└─────────────┘    └─────┘    └────────────────┘    └──────────────────┘    └───────────┘    └──────────────┘
```

All components except the LLM run locally. The LLM can be local (Ollama, LM Studio) or a remote OpenAI-compatible API.

### n8n Integration (Function Calling)

The assistant supports tool use via [n8n](https://n8n.io/) webhooks. When the LLM decides an action is needed (e.g. "turn off the lights"), it triggers a function call routed to an n8n workflow via webhook:

- Smart home control (Home Assistant)
- Calendar queries (Google Calendar)
- Sending messages (Telegram/SMS)
- Shopping list management (Notion/Todoist)
- Web search
- Reminders

See [`integrations/n8n/README.md`](integrations/n8n/README.md) for setup instructions and example workflows.

| Component      | Role                   | Backend                          |
| -------------- | ---------------------- | -------------------------------- |
| Pipecat        | Pipeline orchestration | Python framework by Daily.co     |
| faster-whisper | Speech-to-Text         | CTranslate2 Whisper              |
| LLM            | Conversation           | Any OpenAI-compatible API        |
| Kokoro         | Text-to-Speech         | Local neural TTS                 |

## Requirements

- Python 3.10+
- Docker & Docker Compose (for the containerised stack)
- ~1 GB for the faster-whisper STT model
- ~500 MB for the Kokoro TTS model
- Additional RAM/VRAM depending on the LLM you choose (see LLM options below)
- PortAudio (for local microphone access in non-Docker mode)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/jayjaybeeuk/local-voice-assistant.git
cd local-voice-assistant
pip install -r requirements.txt
```

### 2. Download STT and TTS models

```bash
python scripts/download_models.py
```

### 3. Choose an LLM backend (see options below), then run

```bash
python app.py        # local audio mode (microphone → speaker)
python app.py --ws   # WebSocket mode (for the web UI)
```

## LLM Backend Options

The assistant works with any OpenAI-compatible API. Set `base_url`, `model`, and (if needed) `api_key` in `config.yaml`, or override them at runtime via environment variables in `.env`.

### Option A — External API (OpenAI, OpenRouter, etc.)

No local GPU required. Set in `.env`:

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
```

Then run `docker compose up`.

### Option B — Local Ollama (Docker)

Runs Ollama as a container on the same Docker network — no `host.docker.internal` needed.

```bash
docker compose --profile ollama up
# First run: pull a model
docker exec ollama ollama pull llama3.2:3b
```

In `config.yaml`:

```yaml
llm:
  base_url: "http://ollama:11434/v1"
  model: "llama3.2:3b"
```

### Option C — Native Ollama (Mac, recommended for Apple Silicon)

Native Ollama uses Apple Metal GPU acceleration automatically — significantly faster than running inside Docker. Install via Homebrew:

```bash
brew install ollama
ollama serve &
ollama pull llama3.2:3b
```

In `config.yaml`:

```yaml
llm:
  base_url: "http://host.docker.internal:11434/v1"  # if running the assistant in Docker
  # base_url: "http://localhost:11434/v1"            # if running the assistant natively
  model: "llama3.2:3b"
```

**Good small models for a 16 GB MacBook:**

| Model | Size | Notes |
|-------|------|-------|
| `llama3.2:3b` | ~2 GB | Fast, snappy responses |
| `qwen2.5:3b` | ~2 GB | Strong instruction following |
| `gemma3:4b` | ~3 GB | Google, good quality |
| `phi4-mini` | ~2.5 GB | Microsoft, efficient |

### Option D — LM Studio (local, GUI)

Prefer a graphical interface? Load any GGUF model in [LM Studio](https://lmstudio.ai), start the local server, and set the bind address to `0.0.0.0` in LM Studio's server settings.

In `config.yaml`:

```yaml
llm:
  base_url: "http://host.docker.internal:1234/v1"  # if running the assistant in Docker
  # base_url: "http://localhost:1234/v1"            # if running the assistant natively
  model: "google/gemma-4-e2b"                       # match the model ID shown in LM Studio
```

No API key is needed for LM Studio. To find the exact model ID:

```bash
curl http://localhost:1234/v1/models
```

## Configuration

`config.yaml` is the single source of truth for the Python backend. It is read once at startup. `.env` variables (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `N8N_BASE_URL`) override the corresponding `config.yaml` values at runtime.

Key settings:

| Key | Description |
|-----|-------------|
| `llm.base_url` | OpenAI-compatible endpoint |
| `llm.model` | Model name as reported by the API |
| `llm.system_prompt` | Assistant persona/behaviour |
| `stt.model_size` | Whisper model size (`base.en`, `small.en`, etc.) |
| `tts.voice` | Kokoro voice ID (see comments in `config.yaml`) |
| `tts.speed` | Playback speed multiplier |
| `vad.*` | Voice activity detection thresholds |

## Docker (Full Stack)

```bash
cp .env.example .env
# Edit .env to set your LLM backend (see options above)
docker compose up
```

This starts:
- `voice-assistant` backend on port **8765**
- Web UI on port **3002**

Open **http://localhost:3002** and tap the microphone button.

| Service         | Port  | Started by default    |
| --------------- | ----- | --------------------- |
| voice-assistant | 8765  | ✅ always             |
| web UI          | 3002  | ✅ always             |
| ollama          | 11434 | ❌ opt-in: `--profile ollama` |
| n8n             | 5678  | ❌ opt-in: `--profile tools`  |

### With NVIDIA GPU (Ollama only)

```bash
docker compose --profile ollama -f docker-compose.yml -f docker-compose.gpu.yml up
```

### Linux: local microphone/speaker mode

```bash
docker compose -f docker-compose.yml -f docker-compose.linux-audio.yml up
```

This overrides the voice-assistant command to `python app.py` (local audio) and mounts `/dev/snd`.

### Optional: n8n workflow tools

```bash
docker compose --profile tools up
```

## n8n Integration Notes

Tool calls are sent to n8n via HTTP webhooks defined in `config.yaml`:

- Base URL: `n8n.base_url` (default `http://localhost:5678`)
- Per-tool paths: `n8n.webhooks.*`

When `voice-assistant` runs in Docker Compose, `N8N_BASE_URL=http://n8n:5678` is set automatically so tool calls resolve on the Compose network. Override it in `.env` to point at an external n8n instance.

If you do not need tools, leave n8n stopped — voice chat still works; only tool calls return an error response.

## Web UI

The Next.js frontend (`web/`) provides a browser-based voice chat interface.

### Features

- **Start/Stop voice chat** — large mic button to toggle; red pulse when active
- **Real-time audio visualiser** — live mic levels with glow effects (green = you, indigo = AI)
- **Live transcript panel** — chat-bubble style conversation history
- **Configurable LLM endpoint** — settings panel (gear icon) to point at any OpenAI-compatible API
- **Test Connection** — verify the endpoint responds before saving
- **Response latency display** — end-to-end response time shown per message
- **Persistent settings** — endpoint config saved to `localStorage`
- **Dark theme** — Inter font, indigo accents

### Running (Docker — recommended)

```bash
cp .env.example .env
docker compose up
```

Open **http://localhost:3002**.

### Running (local dev)

```bash
# Terminal 1: WebSocket backend
python app.py --ws

# Terminal 2: Web UI
cd web && npm install && npm run dev
```

Open **http://localhost:3000**.

### Endpoint Configuration

Click the gear icon to configure the endpoint URL, API key, and model. Changes are saved to `localStorage` in the browser. To change the backend's LLM, edit `config.yaml` and restart the Python process.

## License

MIT
