# Local Voice Assistant — Web Frontend

A modern Next.js frontend for a local voice assistant powered by [Pipecat](https://github.com/pipecat-ai/pipecat) and Daily's WebRTC transport.

![Screenshot placeholder](https://via.placeholder.com/800x400/1e1e2e/6366f1?text=Voice+Assistant+UI)

## Tech Stack

- **Next.js 14+** (App Router, TypeScript)
- **Tailwind CSS** — dark theme with accent colours
- **Daily React SDK** — WebRTC transport
- **Pipecat** — backend voice AI pipeline

## Quick Start

```bash
cd web
cp .env.example .env.local
# Edit .env.local with your Daily API key and room URL

npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Connecting to Pipecat Backend

The backend must use `DailyTransport` from pipecat:

```python
from pipecat.transports.services.daily import DailyTransport

transport = DailyTransport(
    room_url="https://your-domain.daily.co/your-room",
    token="bot-token",
    bot_name="Voice Assistant",
)
```

### Flow:
1. User clicks **Connect** in the frontend
2. Frontend calls `POST /api/connect` which creates/returns a Daily room URL + token
3. Frontend joins the room via Daily SDK
4. Pipecat backend joins the same room and handles audio processing

## Project Structure

```
web/
├── app/            # Next.js App Router pages & API routes
├── components/     # React components (VoiceAssistant, Controls, etc.)
├── hooks/          # Custom hooks (useVoiceConnection, useAudioLevel)
└── lib/            # Configuration and utilities
```

## Features

- 🎙️ **Push-to-talk & hands-free (VAD)** modes
- 📊 **Real-time audio visualiser** with glow effects
- 💬 **Live transcript** showing user & AI messages
- 🔌 **Connection status** indicator
- ⚙️ **Settings panel** for mic and mode selection
- 🌙 **Dark theme** with Inter font

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DAILY_API_KEY` | Your Daily.co API key |
| `DAILY_ROOM_URL` | Daily room URL (dev/mock) |
| `DAILY_TOKEN` | Daily meeting token |
| `PIPECAT_BACKEND_URL` | Pipecat backend endpoint |

## License

MIT
