"""
Local Voice Assistant - Pipecat Pipeline
Audio Input → VAD → faster-whisper STT → Qwen3-8B LLM (with tools) → Kokoro TTS → Audio Output
"""

import asyncio
import json
import logging
import yaml
import numpy as np
from pathlib import Path

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


async def main():
    config = load_config()

    # Initialize n8n tools service
    tools_service = N8nToolsService(config.get("n8n", {}))

    # Local audio transport (microphone + speaker)
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

    # STT - faster-whisper (local)
    stt = FasterWhisperSTTService(
        model_size=config["stt"]["model_size"],
        device=config["stt"]["device"],
        compute_type=config["stt"]["compute_type"],
    )

    # LLM - Qwen3-8B via Ollama (OpenAI-compatible) with function calling
    llm = OpenAILLMService(
        api_key="not-needed",
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"],
        params={"temperature": 0.7, "max_tokens": 256},
    )
    llm.system_prompt = config["llm"]["system_prompt"]

    # Register tools with the LLM
    llm.tools = tools_service.get_tool_definitions()

    # Handle function calls from the LLM
    @llm.function("control_smart_home")
    @llm.function("query_calendar")
    @llm.function("send_message")
    @llm.function("add_to_list")
    @llm.function("web_search")
    @llm.function("set_reminder")
    async def on_function_call(function_name: str, tool_call_id: str, arguments: dict, llm_instance, context, result_callback):
        """Handle any tool function call by forwarding to n8n."""
        logger.info(f"Function call: {function_name}({arguments})")
        result = await tools_service.execute_tool(function_name, arguments)
        await result_callback(result)

    # TTS - Kokoro (local)
    tts = KokoroTTSService(
        voice=config["tts"]["voice"],
        speed=config["tts"]["speed"],
        sample_rate=config["tts"]["sample_rate"],
    )

    # Build pipeline: input → STT → LLM → TTS → output
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            llm,
            tts,
            transport.output(),
        ]
    )

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


if __name__ == "__main__":
    asyncio.run(main())
