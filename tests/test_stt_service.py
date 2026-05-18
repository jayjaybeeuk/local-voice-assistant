import pytest
import numpy as np
from unittest.mock import MagicMock

from services.stt_service import FasterWhisperSTTService


@pytest.fixture
def service():
    svc = FasterWhisperSTTService(model_size="tiny.en", device="cpu", compute_type="int8")
    return svc


def _silence(seconds=1, sample_rate=16000):
    return np.zeros(sample_rate * seconds, dtype=np.int16).tobytes()


def _mock_model(*segment_texts):
    segments = []
    for text in segment_texts:
        seg = MagicMock()
        seg.text = text
        segments.append(seg)
    model = MagicMock()
    model.transcribe.return_value = (iter(segments), MagicMock())
    return model


@pytest.mark.asyncio
async def test_run_stt_silent_audio_returns_empty(service):
    service._model = _mock_model()
    result = await service.run_stt(_silence())
    assert result == ""


@pytest.mark.asyncio
async def test_run_stt_single_segment(service):
    service._model = _mock_model("hello world")
    result = await service.run_stt(_silence())
    assert result == "hello world"


@pytest.mark.asyncio
async def test_run_stt_joins_multiple_segments(service):
    service._model = _mock_model("hello", "world")
    result = await service.run_stt(_silence(2))
    assert result == "hello world"


@pytest.mark.asyncio
async def test_run_stt_strips_whitespace(service):
    service._model = _mock_model("  hello  ", "  world  ")
    result = await service.run_stt(_silence())
    assert result == "hello world"


@pytest.mark.asyncio
async def test_run_stt_converts_int16_to_float32(service):
    captured = {}
    original_transcribe = None

    def mock_transcribe(audio_array, **kwargs):
        captured["audio"] = audio_array
        return iter([]), MagicMock()

    service._model = MagicMock()
    service._model.transcribe.side_effect = mock_transcribe

    pcm = np.array([0, 16384, -16384, 32767], dtype=np.int16).tobytes()
    await service.run_stt(pcm)

    assert captured["audio"].dtype == np.float32
    assert captured["audio"].max() <= 1.0
    assert captured["audio"].min() >= -1.0
