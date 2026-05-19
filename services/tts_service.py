"""Custom Kokoro TTS service for Pipecat."""

import numpy as np
import soundfile as sf
import io

from pipecat.services.tts_service import TTSService
from pipecat.frames.frames import AudioRawFrame, TextFrame


class KokoroTTSService(TTSService):
    """Local TTS using Kokoro."""

    def __init__(self, voice: str = "af_heart", speed: float = 1.0, sample_rate: int = 24000, pitch_semitones: float = 0):
        super().__init__()
        self._voice = voice
        self._speed = speed
        self._sample_rate = sample_rate
        self._pitch_semitones = pitch_semitones
        self._pipeline = None
        self._ensure_model()

    def _ensure_model(self):
        if self._pipeline is None:
            from kokoro import KPipeline
            self._pipeline = KPipeline(lang_code="a")

    @staticmethod
    def _pitch_shift(audio_int16: np.ndarray, semitones: float) -> np.ndarray:
        """Shift pitch by semitones without changing duration (numpy-only)."""
        if semitones == 0:
            return audio_int16
        factor = 2.0 ** (semitones / 12.0)
        n = len(audio_int16)
        audio_f32 = audio_int16.astype(np.float32) / 32768.0
        # Compress/expand to shift pitch, then restore original length
        compressed_len = max(1, int(n / factor))
        compressed = np.interp(np.linspace(0, n - 1, compressed_len), np.arange(n), audio_f32)
        restored = np.interp(np.linspace(0, compressed_len - 1, n), np.arange(compressed_len), compressed)
        return (np.clip(restored, -1.0, 1.0) * 32767).astype(np.int16)

    async def run_tts(self, text: str) -> bytes:
        """Convert text to audio bytes."""
        self._ensure_model()

        audio_segments = []
        for _, _, audio in self._pipeline(text, voice=self._voice, speed=self._speed):
            if audio is not None:
                audio_segments.append(audio)

        if not audio_segments:
            return b""

        audio_int16 = (np.concatenate(audio_segments) * 32767).astype(np.int16)
        if self._pitch_semitones:
            audio_int16 = self._pitch_shift(audio_int16, self._pitch_semitones)
        return audio_int16.tobytes()

    async def process_frame(self, frame, direction):
        """Process text frames into audio."""
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame):
            audio_bytes = await self.run_tts(frame.text)
            if audio_bytes:
                await self.push_frame(
                    AudioRawFrame(
                        audio=audio_bytes,
                        sample_rate=self._sample_rate,
                        num_channels=1,
                    )
                )
        else:
            await self.push_frame(frame)
