"""
Local Voice Assistant - Pipecat Pipeline
Audio Input → VAD → faster-whisper STT → Qwen3-8B LLM → Kokoro TTS → Audio Output
"""

import asyncio
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


def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


async def main():
    config = load_config()

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

    # LLM - Qwen3-8B via Ollama (OpenAI-compatible)
    llm = OpenAILLMService(
        api_key="not-needed",
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"],
        params={"temperature": 0.7, "max_tokens": 256},
    )
    llm.system_prompt = config["llm"]["system_prompt"]

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
    print("   Press Ctrl+C to stop.")

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        await task.queue_frame(EndFrame())


if __name__ == "__main__":
    asyncio.run(main())
