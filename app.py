"""
Local Voice Assistant - Pipecat Pipeline
Supports both local audio and WebSocket transport (for web UI on port 8765).

Audio Input → VAD → faster-whisper STT → Qwen3-8B LLM (with tools) → Kokoro TTS → Audio Output
"""

import asyncio
import json
import logging
import os
import sys
import yaml
import numpy as np
from pathlib import Path

import torch
import aiohttp
import websockets
from silero_vad import load_silero_vad, VADIterator

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.frames.frames import (
    AudioRawFrame,
    TextFrame,
    EndFrame,
)
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.local.audio import LocalAudioTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer

from services.stt_service import FasterWhisperSTTService
from services.tts_service import KokoroTTSService
from services.tools_service import N8nToolsService, handle_function_call

logger = logging.getLogger(__name__)

HISTORY_MAX_TURNS = 20  # rolling window: keep last N user+assistant pairs


def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Overlay web/config.local.json if present (written by the settings panel)
    local_config_path = Path(__file__).parent / "web" / "config.local.json"
    if local_config_path.exists():
        try:
            with open(local_config_path) as f:
                local = json.load(f)
            if local.get("endpointUrl"):
                config["llm"]["base_url"] = local["endpointUrl"]
            if local.get("model"):
                config["llm"]["model"] = local["model"]
            if local.get("apiKey"):
                config["llm"]["api_key"] = local["apiKey"]
        except Exception as exc:
            logger.warning("Could not load config.local.json: %s", exc)

    # Allow container/runtime override for n8n webhook routing.
    n8n_base_url = os.getenv("N8N_BASE_URL")
    if n8n_base_url:
        config.setdefault("n8n", {})["base_url"] = n8n_base_url

    # Allow container/runtime overrides for the LLM provider.
    llm_base_url = os.getenv("LLM_BASE_URL")
    if llm_base_url:
        config.setdefault("llm", {})["base_url"] = llm_base_url

    llm_model = os.getenv("LLM_MODEL")
    if llm_model:
        config.setdefault("llm", {})["model"] = llm_model

    llm_api_key = os.getenv("LLM_API_KEY")
    if llm_api_key:
        config.setdefault("llm", {})["api_key"] = llm_api_key

    return config


def build_stt_tts(config):
    """Create only STT and TTS — used by the WebSocket path."""
    stt = FasterWhisperSTTService(
        model_size=config["stt"]["model_size"],
        device=config["stt"]["device"],
        compute_type=config["stt"]["compute_type"],
    )
    tts = KokoroTTSService(
        voice=config["tts"]["voice"],
        speed=config["tts"]["speed"],
        sample_rate=config["tts"]["sample_rate"],
    )
    return stt, tts


def build_services(config):
    """Create STT, LLM (with tool registrations), TTS, and tools services — used by local mode."""
    tools_service = N8nToolsService(config.get("n8n", {}))

    stt = FasterWhisperSTTService(
        model_size=config["stt"]["model_size"],
        device=config["stt"]["device"],
        compute_type=config["stt"]["compute_type"],
    )

    llm = OpenAILLMService(
        api_key=config["llm"].get("api_key", "not-needed") or "not-needed",
        base_url=config["llm"]["base_url"],
        settings=OpenAILLMService.Settings(
            model=config["llm"]["model"],
            temperature=0.7,
            max_tokens=256,
        ),
    )

    tts = KokoroTTSService(
        voice=config["tts"]["voice"],
        speed=config["tts"]["speed"],
        sample_rate=config["tts"]["sample_rate"],
    )

    return stt, llm, tts, tools_service


async def call_llm_api(config: dict, messages: list) -> str:
    """Call the OpenAI-compatible LLM API with a full message history."""
    url = f"{config['llm']['base_url']}/chat/completions"
    api_key = config["llm"].get("api_key", "not-needed") or "not-needed"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": config["llm"]["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 256,
    }
    logger.debug("LLM request → %s  model=%s", url, config["llm"]["model"])
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            text = await resp.text()
            raise RuntimeError(f"HTTP {resp.status} from {url}: {text[:400]}")


class WebSocketAudioServer:
    """WebSocket server that bridges browser audio into the voice pipeline."""

    # Silero VAD processes audio in 512-sample windows at 16 kHz
    VAD_CHUNK_SAMPLES = 512
    VAD_CHUNK_BYTES = VAD_CHUNK_SAMPLES * 2  # 16-bit mono

    def __init__(self, config, host="0.0.0.0", port=8765):
        self.config = config
        self.host = host
        self.port = port
        print("Loading STT and TTS models...", flush=True)
        self.stt, self.tts = build_stt_tts(config)
        print("Loading VAD model...", flush=True)
        self._vad_model = load_silero_vad()
        print("Models ready.", flush=True)

    async def handle_client(self, websocket, path=None):
        logger.info("Web client connected")
        config = self.config
        secret_key = config.get("server", {}).get("secret_key", "")

        # Authenticate if a secret key is configured
        if secret_key:
            try:
                auth_raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                if isinstance(auth_raw, bytes):
                    auth_raw = auth_raw.decode("utf-8")
                auth = json.loads(auth_raw)
                if auth.get("token") != secret_key:
                    await websocket.send(json.dumps({"type": "error", "message": "Unauthorized"}))
                    await websocket.close()
                    logger.warning("Client rejected: invalid token")
                    return
            except (asyncio.TimeoutError, json.JSONDecodeError, Exception) as exc:
                logger.warning("Auth failed: %s", exc)
                await websocket.close()
                return

        stt, tts = self.stt, self.tts

        # Per-connection VAD — shares the model, has its own state
        vad_cfg = config.get("vad", {})
        vad = VADIterator(
            self._vad_model,
            threshold=vad_cfg.get("threshold", 0.5),
            sampling_rate=config["audio"]["sample_rate"],
            min_silence_duration_ms=vad_cfg.get("min_silence_duration_ms", 600),
            speech_pad_ms=100,
        )

        # Per-session conversation history
        history: list = [{"role": "system", "content": config["llm"]["system_prompt"]}]

        audio_buffer = bytearray()
        speech_buffer = bytearray()
        in_speech = False

        async def send_json(data: dict):
            try:
                await websocket.send(json.dumps(data))
            except Exception:
                pass

        async def process_utterance(utterance_bytes: bytes):
            try:
                text = await stt.run_stt(utterance_bytes)
            except Exception as exc:
                logger.error("STT error: %s", exc)
                await send_json({"type": "error", "message": f"STT failed: {exc}"})
                return

            if not text or not text.strip():
                return

            logger.info("STT: %s", text)
            await send_json({"type": "transcript", "role": "user", "text": text.strip()})
            history.append({"role": "user", "content": text.strip()})

            try:
                response = await call_llm_api(config, history)
            except Exception as exc:
                logger.error("LLM error [%s]: %s", type(exc).__name__, exc)
                await send_json({"type": "error", "message": f"LLM failed: {type(exc).__name__}: {exc}"})
                history.pop()
                return

            logger.info("LLM: %s", response)
            history.append({"role": "assistant", "content": response})

            if len(history) > 1 + HISTORY_MAX_TURNS * 2:
                history[1:] = history[1 - HISTORY_MAX_TURNS * 2 :]

            await send_json({"type": "transcript", "role": "assistant", "text": response})

            try:
                audio_data = await tts.run_tts(response)
            except Exception as exc:
                logger.error("TTS error: %s", exc)
                await send_json({"type": "error", "message": f"TTS failed: {exc}"})
                return

            if audio_data:
                await websocket.send(audio_data)

        try:
            async for message in websocket:
                if not isinstance(message, bytes):
                    continue

                audio_buffer.extend(message)

                # Drain the buffer in 512-sample (32 ms) VAD windows
                while len(audio_buffer) >= self.VAD_CHUNK_BYTES:
                    chunk = bytes(audio_buffer[:self.VAD_CHUNK_BYTES])
                    audio_buffer = audio_buffer[self.VAD_CHUNK_BYTES:]

                    arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                    event = vad(torch.from_numpy(arr), return_seconds=False)

                    if event and "start" in event:
                        in_speech = True

                    if in_speech:
                        speech_buffer.extend(chunk)

                    if event and "end" in event:
                        in_speech = False
                        utterance = bytes(speech_buffer)
                        speech_buffer = bytearray()
                        vad.reset_states()
                        # Ignore tiny blips (< ~200 ms)
                        if len(utterance) >= self.VAD_CHUNK_BYTES * 6:
                            await process_utterance(utterance)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Web client disconnected")
        except Exception as exc:
            logger.error("WebSocket session error: %s", exc)

    async def start(self):
        logger.info(f"WebSocket audio server listening on ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # run forever


async def run_local(config):
    """Run with local audio transport."""
    stt, llm, tts, _ = build_services(config)

    transport = LocalAudioTransport(
        input_sample_rate=config["audio"]["sample_rate"],
        output_sample_rate=config["tts"]["sample_rate"],
        vad_analyzer=SileroVADAnalyzer(
            params={
                "threshold": config["vad"]["threshold"],
                "min_speech_duration_ms": config["vad"]["min_speech_duration_ms"],
                "min_silence_duration_ms": config["vad"]["min_silence_duration_ms"],
            }
        ),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        llm,
        tts,
        transport.output(),
    ])

    task = PipelineTask(pipeline)
    runner = PipelineRunner()

    print("🎙️  Local Voice Assistant ready! Speak into your microphone...")
    print("   n8n tools enabled:", list(config.get("n8n", {}).get("webhooks", {}).keys()))
    print("   Press Ctrl+C to stop.")

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        await task.queue_frame(EndFrame())


async def main():
    config = load_config()
    mode = "websocket" if "--ws" in sys.argv or "--websocket" in sys.argv else "local"

    if mode == "websocket":
        print("🌐 Starting WebSocket voice server on ws://0.0.0.0:8765")
        print("   Connect via the web UI at http://localhost:3002 (Docker) or http://localhost:3000 (dev)")
        print(f"   LLM: {config['llm']['base_url']}  model={config['llm']['model']}")
        server = WebSocketAudioServer(config, port=8765)
        await server.start()
    else:
        await run_local(config)


if __name__ == "__main__":
    asyncio.run(main())
