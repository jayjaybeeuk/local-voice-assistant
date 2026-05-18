# Local Voice Assistant

A fully local, real-time duplex voice conversation system using Pipecat for pipeline orchestration.

## Architecture

```
┌─────────────┐    ┌─────┐    ┌───────────────┐    ┌───────────┐    ┌───────────┐    ┌──────────────┐
│ Microphone  │───▶│ VAD │───▶│ faster-whisper │───▶│ Qwen3-8B  │───▶│ Kokoro TTS│───▶│   Speaker    │
│   Input     │    │     │    │     (STT)      │    │  (Ollama)  │    │           │    │   Output     │
└─────────────┘    └─────┘    └───────────────┘    └───────────┘    └───────────┘    └──────────────┘
```

All components run locally — no cloud APIs required.

### n8n Integration (Function Calling)

The assistant supports tool use via [n8n](https://n8n.io/) webhooks. When the LLM decides an action is needed (e.g., "turn off the lights"), it triggers a function call that is routed to an n8n workflow via webhook. This enables:

- 🏠 Smart home control (Home Assistant)
- 📅 Calendar queries (Google Calendar)
- 💬 Sending messages (Telegram/SMS)
- 🛒 Shopping list management (Notion/Todoist)
- 🔍 Web search
- ⏰ Reminders

See [`integrations/n8n/README.md`](integrations/n8n/README.md) for setup instructions and example workflows.

| Component      | Role                   | Backend                        |
| -------------- | ---------------------- | ------------------------------ |
| Pipecat        | Pipeline orchestration | Python framework by Daily.co   |
| faster-whisper | Speech-to-Text         | CTranslate2 Whisper            |
| Qwen3-8B       | LLM (conversation)     | Ollama (OpenAI-compatible API) |
| Kokoro         | Text-to-Speech         | Local neural TTS               |

## Requirements

- Python 3.10+
- Docker & Docker Compose (for Ollama)
- ~8GB VRAM for Qwen3-8B (or CPU with more RAM)
- ~1GB for faster-whisper model
- ~500MB for Kokoro TTS model
- PortAudio (for local microphone access)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/jayjaybeeuk/local-voice-assistant.git
cd local-voice-assistant
pip install -r requirements.txt
```

### 2. Download models

```bash
# Download faster-whisper and Kokoro models
python scripts/download_models.py

# Pull Qwen3-8B in Ollama
docker compose up -d ollama
docker exec ollama ollama pull qwen3:8b
```

### 3. Run

```bash
# Start Ollama (if not already running)
docker compose up -d ollama

# Run the voice assistant
python app.py
```

## Run Voice Assistant With External OpenAI-Compatible API (No Ollama)

If you want to run only the voice assistant and use an external OpenAI-compatible API
(for example OpenAI, OpenRouter, Together, or a remote vLLM server), you do not need
to run the `ollama` Docker service.

### 1. Install dependencies

```bash
pip install -r requirements.txt
python scripts/download_models.py
```

### 2. Update `config.yaml`

Set your LLM endpoint and model:

```yaml
llm:
  base_url: "https://api.openai.com/v1" # or your OpenAI-compatible endpoint
  model: "gpt-4o-mini" # or provider-specific model name
```

Set your API key in the environment before starting:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

### 3. Start only the assistant

```bash
python app.py
```

For WebSocket mode (with the web UI):

```bash
python app.py --ws
```

## Configuration

Edit `config.yaml` to customize:

- LLM endpoint and model
- STT model size
- TTS voice and speed
- Audio device settings

## Docker (Full Stack)

```bash
cp .env.example .env
docker compose up
```

This starts both Ollama and the voice assistant. Ollama runs in CPU mode by default.

### With NVIDIA GPU

If you have an NVIDIA GPU with drivers installed, use the GPU override to pass the device to Ollama:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
```

## Docker: Voice Assistant With External LLM Endpoint

Use the same `voice-assistant` service for both internal and external LLM modes.

### 1. Create your `.env`

```bash
cp .env.example .env
```

### 2. Choose one mode in `.env`

1. Internal Ollama mode:
   Set `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` to empty values in `.env`.
2. External API mode:
   Fill `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` with your provider values.

Example external values:

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your_api_key_here
```

### 3. Run with Docker Compose

```bash
docker compose up --no-deps voice-assistant
```

Notes:

1. `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` override `config.yaml` at runtime.
2. If external values are set, the assistant uses your external endpoint.
3. If external values are empty, the assistant uses the local `config.yaml` LLM settings.
4. If you also want tools in Docker, start n8n with:

```bash
docker compose --profile tools up -d n8n
```

## n8n Integration Notes

Tool calls are sent to n8n via HTTP webhooks defined in `config.yaml`:

- Base URL: `n8n.base_url` (default `http://localhost:5678`)
- Per-tool paths: `n8n.webhooks.*`

An optional `n8n` service is included in `docker-compose.yml` under the `tools` profile.

Start it with:

```bash
docker compose --profile tools up -d n8n
```

When `voice-assistant` runs in Docker Compose, it uses `N8N_BASE_URL=http://n8n:5678`
so tool calls resolve automatically on the Compose network.

You can still use an external n8n instance by changing `n8n.base_url` in `config.yaml`
or overriding `N8N_BASE_URL`.

If you do not need tools:

1. Leave n8n stopped.
2. Voice chat still works; only tool calls return an error response.

## Web UI

The Next.js frontend (`web/`) provides a full browser-based voice chat interface.

### Features

- **Start/Stop voice chat** — large mic button to toggle; red pulse when active
- **Real-time audio visualiser** — live mic levels with glow effects (green = you, indigo = AI)
- **Live transcript panel** — chat-bubble style conversation history
- **Configurable LLM endpoint** — settings panel (gear icon) lets you point at any OpenAI-compatible API (local Ollama, OpenAI, etc.), with a **Test Connection** button to verify
- **Response latency display** — discreet ⚡ ms figure showing end-to-end response time
- **Persistent settings** — endpoint config saved to localStorage, survives refreshes
- **Dark theme** — Inter font, indigo accents, minimal design

### Running

```bash
# Terminal 1: Start the WebSocket backend
python app.py --ws

# Terminal 2: Start the web UI
cd web && npm install && npm run dev
```

Open http://localhost:3000 and tap the microphone button to start a voice conversation.

### Endpoint Configuration

Click the ⚙️ gear icon to configure:

- **Endpoint URL** — e.g. `http://localhost:11434/v1` (Ollama) or `https://api.openai.com/v1`
- **API Key** — optional, for remote providers
- **Model** — e.g. `qwen3:8b`, `gpt-4o`, etc.

Hit **Test Connection** to verify the endpoint responds, then **Save**. The backend polls `/api/config` to pick up changes.

## License

MIT
