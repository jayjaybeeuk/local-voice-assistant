#!/usr/bin/env python3
"""Download required models for the local voice assistant."""

import subprocess
import sys


def main():
    print("📥 Downloading faster-whisper model (base.en)...")
    # faster-whisper auto-downloads on first use, but we can pre-cache it
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        del model
        print("✅ faster-whisper model ready")
    except Exception as e:
        print(f"⚠️  faster-whisper download issue: {e}")
        print("   It will download automatically on first run.")

    print("\n📥 Downloading Kokoro TTS model...")
    try:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code="a")
        del pipeline
        print("✅ Kokoro TTS model ready")
    except Exception as e:
        print(f"⚠️  Kokoro download issue: {e}")
        print("   It will download automatically on first run.")

    print("\n📥 To pull Qwen3-8B in Ollama, run:")
    print("   docker compose up -d ollama")
    print("   docker exec ollama ollama pull qwen3:8b")
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
