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
import struct
import numpy as np
from pathlib import Path

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


def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


class WebSocketAudioServer:
    """Simple WebSocket server that bridges browser audio into a Pipecat pipeline."""

    def __init__(self, config, host="0.0.0.0", port=8765):
        self.config = config
        self.host = host
        self.port = port

    async def handle_client(self, websocket, path=None):
        """Handle a single WebSocket client connection."""
        logger.info("Web client connected")
        config = self.config

        # Initialize services for this session
        tools_service = N8nToolsService(config.get("n8n", {}))

        stt = FasterWhisperSTTService(
            model_size=config["stt"]["model_size"],
            device=config["stt"]["device"],
            compute_type=config["stt"]["compute_type"],
        )

        llm = OpenAILLMService(
            api_key="not-needed",
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

        # Simple streaming loop: receive audio → STT → LLM → TTS → send audio back
        # For a full Pipecat pipeline with WebSocket transport, we bridge manually:
        audio_buffer = bytearray()
        sample_rate = config["audio"]["sample_rate"]

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    audio_buffer.extend(message)

                    # Process in chunks (0.5s of audio = 16000 samples = 32000 bytes at 16-bit)
                    chunk_size = sample_rate  # 1 second of samples
                    byte_chunk = chunk_size * 2  # 16-bit = 2 bytes per sample

                    while len(audio_buffer) >= byte_chunk:
                        chunk = bytes(audio_buffer[:byte_chunk])
                        audio_buffer = audio_buffer[byte_chunk:]

                        # Feed to STT
                        frame = AudioRawFrame(
                            audio=chunk,
                            sample_rate=sample_rate,
                            num_channels=1,
                        )
                        text = await stt.run_stt(frame)
                        if text and text.strip():
                            logger.info(f"STT: {text}")
                            # Get LLM response
                            response = await llm.generate(text)
                            if response:
                                logger.info(f"LLM: {response}")
                                # Generate TTS
                                audio_data = await tts.run_tts(response)
                                if audio_data:
                                    # Send audio back as raw PCM int16
                                    await websocket.send(audio_data)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Web client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    async def start(self):
        logger.info(f"WebSocket audio server listening on ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # run forever


async def run_local(config):
    """Run with local audio transport (original mode)."""
    tools_service = N8nToolsService(config.get("n8n", {}))

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

    stt = FasterWhisperSTTService(
        model_size=config["stt"]["model_size"],
        device=config["stt"]["device"],
        compute_type=config["stt"]["compute_type"],
    )

    llm = OpenAILLMService(
        api_key="not-needed",
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
