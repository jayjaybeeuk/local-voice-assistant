"""
Local Voice Assistant - Pipecat Pipeline
Supports both local audio and WebSocket transport (for web UI on port 8765).

Audio Input → VAD → faster-whisper STT → Qwen3-8B LLM (with tools) → Kokoro TTS → Audio Output
"""

import asyncio
import json
import logging
import sys
import yaml
import numpy as np
from pathlib import Path

import aiohttp
import websockets

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.frames.frames import (
    AudioRawFrame,
    TextFrame,
    LLMMessagesFrame,
    EndFrame,
)
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.local.audio import LocalAudioTransport
from pipecat.vad.silero import SileroVADAnalyzer

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

    return config


def build_services(config):
    """Create STT, LLM (with tool registrations), TTS, and tools services."""
    tools_service = N8nToolsService(config.get("n8n", {}))

    stt = FasterWhisperSTTService(
        model_size=config["stt"]["model_size"],
        device=config["stt"]["device"],
        compute_type=config["stt"]["compute_type"],
    )

    llm = OpenAILLMService(
        api_key=config["llm"].get("api_key", "not-needed") or "not-needed",
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"],
        params={"temperature": 0.7, "max_tokens": 256},
    )
    llm.system_prompt = config["llm"]["system_prompt"]
    llm.tools = tools_service.get_tool_definitions()

    @llm.function("control_smart_home")
    @llm.function("query_calendar")
    @llm.function("send_message")
    @llm.function("add_to_list")
    @llm.function("web_search")
    @llm.function("set_reminder")
    async def on_function_call(function_name, tool_call_id, arguments, llm_instance, context, result_callback):
        result = await tools_service.execute_tool(function_name, arguments)
        await result_callback(result)

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
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            text = await resp.text()
            raise RuntimeError(f"LLM API returned {resp.status}: {text}")


class WebSocketAudioServer:
    """WebSocket server that bridges browser audio into the voice pipeline."""

    def __init__(self, config, host="0.0.0.0", port=8765):
        self.config = config
        self.host = host
        self.port = port

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

        stt, _, tts, _ = build_services(config)

        # Per-session conversation history
        history: list = [{"role": "system", "content": config["llm"]["system_prompt"]}]

        audio_buffer = bytearray()
        sample_rate = config["audio"]["sample_rate"]
        byte_chunk = sample_rate * 2  # 1 second of 16-bit mono

        async def send_json(data: dict):
            try:
                await websocket.send(json.dumps(data))
            except Exception:
                pass

        try:
            async for message in websocket:
                if not isinstance(message, bytes):
                    continue

                audio_buffer.extend(message)

                while len(audio_buffer) >= byte_chunk:
                    chunk = bytes(audio_buffer[:byte_chunk])
                    audio_buffer = audio_buffer[byte_chunk:]

                    try:
                        text = await stt.run_stt(chunk)
                    except Exception as exc:
                        logger.error("STT error: %s", exc)
                        await send_json({"type": "error", "message": f"STT failed: {exc}"})
                        continue

                    if not text or not text.strip():
                        continue

                    logger.info("STT: %s", text)
                    await send_json({"type": "transcript", "role": "user", "text": text.strip()})

                    history.append({"role": "user", "content": text.strip()})

                    try:
                        response = await call_llm_api(config, history)
                    except Exception as exc:
                        logger.error("LLM error: %s", exc)
                        await send_json({"type": "error", "message": f"LLM failed: {exc}"})
                        history.pop()
                        continue

                    logger.info("LLM: %s", response)
                    history.append({"role": "assistant", "content": response})

                    # Rolling window: keep system prompt + last HISTORY_MAX_TURNS*2 messages
                    if len(history) > 1 + HISTORY_MAX_TURNS * 2:
                        history[1:] = history[1 - HISTORY_MAX_TURNS * 2 :]

                    await send_json({"type": "transcript", "role": "assistant", "text": response})

                    try:
                        audio_data = await tts.run_tts(response)
                    except Exception as exc:
                        logger.error("TTS error: %s", exc)
                        await send_json({"type": "error", "message": f"TTS failed: {exc}"})
                        continue

                    if audio_data:
                        await websocket.send(audio_data)

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
        print("   Connect via the web UI at http://localhost:3000")
        server = WebSocketAudioServer(config, port=8765)
        await server.start()
    else:
        await run_local(config)


if __name__ == "__main__":
    asyncio.run(main())
