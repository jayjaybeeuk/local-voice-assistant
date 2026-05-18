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

## License

MIT
