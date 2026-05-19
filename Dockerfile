FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download models so they're baked into the image layer.
# faster-whisper downloads to ~/.cache/huggingface/hub
# Kokoro downloads spacy en_core_web_sm on first KPipeline init
RUN python -c "\
from faster_whisper import WhisperModel; \
print('Downloading Whisper model...'); \
WhisperModel('base.en', device='cpu', compute_type='int8'); \
print('Whisper ready.')"

RUN python -c "\
from kokoro import KPipeline; \
print('Downloading Kokoro + spacy model...'); \
KPipeline(lang_code='a'); \
print('Kokoro ready.')"

ENV PYTHONUNBUFFERED=1
CMD ["python", "app.py", "--ws"]
