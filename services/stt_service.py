"""Custom faster-whisper STT service for Pipecat."""

import numpy as np
from faster_whisper import WhisperModel

from pipecat.services.ai_services import STTService
from pipecat.frames.frames import TranscriptionFrame, AudioRawFrame


class FasterWhisperSTTService(STTService):
    """Local STT using faster-whisper (CTranslate2)."""

    def __init__(self, model_size: str = "base.en", device: str = "auto", compute_type: str = "int8"):
        super().__init__()
        self._model_size = model_size
        self._device = device if device != "auto" else "cuda"
        self._compute_type = compute_type
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            try:
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
            except Exception:
                # Fallback to CPU
                self._model = WhisperModel(
                    self._model_size,
                    device="cpu",
                    compute_type="int8",
                )

    async def run_stt(self, audio: bytes) -> str:
        """Transcribe audio bytes to text."""
        self._ensure_model()

        audio_array = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        segments, _ = self._model.transcribe(
            audio_array,
            beam_size=3,
            language="en",
            vad_filter=True,
        )

        text = " ".join(segment.text.strip() for segment in segments)
        return text

    async def process_frame(self, frame, direction):
        """Process incoming audio frames."""
        await super().process_frame(frame, direction)

        if isinstance(frame, AudioRawFrame):
            text = await self.run_stt(frame.audio)
            if text.strip():
                await self.push_frame(TranscriptionFrame(text=text, user_id="user"))
        else:
            await self.push_frame(frame)
