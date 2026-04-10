"""Whisper local STT service for multilingual voice transcription."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import UploadFile

logger = logging.getLogger(__name__)


class WhisperService:
    """Wrapper around local Whisper model."""

    def __init__(self) -> None:
        self.model_name = os.getenv("WHISPER_MODEL", "tiny").strip() or "tiny"
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            import whisper  # type: ignore
        except Exception as exc:
            raise RuntimeError("Whisper is not installed. Install: pip install openai-whisper") from exc

        logger.info("Loading Whisper model: %s", self.model_name)
        self._model = whisper.load_model(self.model_name)
        return self._model

    @staticmethod
    def detect_language_heuristic(text: str) -> str:
        """Simple heuristic language detector (bonus MVP)."""
        t = (text or "").lower()
        hindi_markers = ["hai", "hua", "bijli", "mahina", "mahine", "kitna", "diesel", "liter", "unit"]
        devnagari_found = any("\u0900" <= ch <= "\u097f" for ch in t)
        if devnagari_found:
            return "hindi"
        if any(marker in t for marker in hindi_markers):
            return "hinglish"
        return "english"

    async def transcribe_upload(self, audio_file: UploadFile) -> dict[str, str]:
        """Transcribe WAV/MP3 audio and return cleaned transcript + heuristic language."""
        filename = str(audio_file.filename or "audio")
        extension = Path(filename).suffix.lower()
        if extension not in {".wav", ".mp3", ".m4a", ".ogg"}:
            raise ValueError("Unsupported audio format. Use wav/mp3/m4a/ogg.")

        model = self._load_model()
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
                content = await audio_file.read()
                if not content:
                    raise ValueError("Uploaded audio file is empty.")
                tmp.write(content)
                temp_path = tmp.name

            result: dict[str, Any] = model.transcribe(temp_path, fp16=False)
            transcript = " ".join(str(result.get("text", "")).split()).strip()
            if not transcript:
                raise ValueError("No speech detected in audio.")

            language = self.detect_language_heuristic(transcript)
            logger.info("Whisper transcript generated (lang=%s)", language)
            return {"transcript": transcript, "language": language}
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
