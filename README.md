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

| Component | Role | Backend |
|-----------|------|---------|
| Pipecat | Pipeline orchestration | Python framework by Daily.co |
| faster-whisper | Speech-to-Text | CTranslate2 Whisper |
| Qwen3-8B | LLM (conversation) | Ollama (OpenAI-compatible API) |
| Kokoro | Text-to-Speech | Local neural TTS |

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

## Configuration

Edit `config.yaml` to customize:
- LLM endpoint and model
- STT model size
- TTS voice and speed
- Audio device settings

## Docker (Full Stack)

```bash
docker compose up
```

This starts both Ollama with Qwen3-8B and the voice assistant app.

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
