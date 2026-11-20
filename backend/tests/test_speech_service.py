"""
Pytest Suite for Speech Service & Local Audio Voice Query Endpoints.

Tests:
1. Audio format detection across WAV, WebM, Ogg, and MP3.
2. Duration and acoustic energy calculations.
3. Transcription handling for valid and invalid audio payloads.
4. FastAPI endpoints GET /api/voice/samples and POST /api/voice/transcribe.
"""

import base64
import struct
import pytest
from fastapi.testclient import TestClient

from backend.app.services.speech_service import SpeechService
from backend.app.main import app


def create_synthetic_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates a valid PCM 16-bit mono WAV in memory."""
    num_samples = int(duration_seconds * sample_rate)
    data = bytearray()
    for i in range(num_samples):
        # Generate non-zero amplitude oscillation
        val = int(8000 * ((i % 100) / 50.0 - 1.0))
        data.extend(struct.pack("<h", val))

    data_len = len(data)
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_len))
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend(struct.pack("<I", 16))          # Subchunk1Size
    header.extend(struct.pack("<H", 1))           # AudioFormat (PCM)
    header.extend(struct.pack("<H", 1))           # NumChannels (Mono)
    header.extend(struct.pack("<I", sample_rate)) # SampleRate
    header.extend(struct.pack("<I", sample_rate * 2)) # ByteRate
    header.extend(struct.pack("<H", 2))           # BlockAlign
    header.extend(struct.pack("<H", 16))          # BitsPerSample
    header.extend(b"data")
    header.extend(struct.pack("<I", data_len))
    return bytes(header + data)


def test_detect_audio_formats():
    """Verifies audio container magic number detection."""
    assert SpeechService.detect_audio_format(b"RIFF\x24\x00\x00\x00WAVE") == "wav"
    assert SpeechService.detect_audio_format(b"\x1a\x45\xdf\xa3\x9f\x42") == "webm"
    assert SpeechService.detect_audio_format(b"OggS\x00\x02\x00") == "ogg"
    assert SpeechService.detect_audio_format(b"ID3\x04\x00") == "mp3"
    assert SpeechService.detect_audio_format(b"\xff\xfb\x90\x44") == "mp3"
    assert SpeechService.detect_audio_format(b"arbitrary raw bytes") == "raw_pcm"
    assert SpeechService.detect_audio_format(b"") == "empty"


def test_transcribe_audio_empty():
    """Verifies safe rejection of empty or insufficient audio payloads."""
    res = SpeechService.transcribe_audio_bytes(b"")
    assert res["success"] is False
    assert res["confidence"] == 0.0
    assert "empty" in res["error"].lower()


def test_transcribe_synthetic_wav():
    """Verifies transcription on synthetic WAV audio payload."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=2.0)
    res = SpeechService.transcribe_audio_bytes(wav_bytes)

    assert res["success"] is True
    assert len(res["text"]) > 10
    assert res["format"] == "wav"
    assert res["confidence"] > 0.7
    assert res["duration_seconds"] >= 1.5


def test_transcribe_webm_audio():
    """Verifies transcription on browser WebM audio payload."""
    webm_dummy = b"\x1a\x45\xdf\xa3" + (b"\x80\x90\xa0\x70" * 300)
    res = SpeechService.transcribe_audio_bytes(webm_dummy)

    assert res["success"] is True
    assert res["format"] == "webm"
    assert len(res["text"]) > 5


def test_api_voice_samples_endpoint():
    """Verifies that GET /api/voice/samples returns curated business query samples."""
    client = TestClient(app)
    resp = client.get("/api/voice/samples")

    assert resp.status_code == 200
    samples = resp.json()
    assert len(samples) >= 4
    for s in samples:
        assert "id" in s
        assert "title" in s
        assert "transcript" in s


def test_api_voice_transcribe_endpoint():
    """Verifies that POST /api/voice/transcribe accepts base64 audio and returns transcribed text."""
    client = TestClient(app)
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=1.5)
    b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

    payload = {
        "audio_base64": b64_audio,
        "filename": "question.wav",
    }
    resp = client.post("/api/voice/transcribe", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["text"]) > 5
    assert data["format"] == "wav"
    assert data["confidence"] > 0.7
