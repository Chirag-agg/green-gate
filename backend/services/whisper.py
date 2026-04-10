"""Local Whisper speech-to-text service."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import UploadFile


class WhisperService:
    """Wrapper around local Whisper model for transcription."""

    def __init__(self) -> None:
        self.model_name = os.getenv("WHISPER_MODEL", "tiny").strip() or "tiny"
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            import whisper  # type: ignore
        except Exception as exc:  # pragma: no cover - import error is runtime environment specific
            raise RuntimeError(
                "Whisper is not installed. Install with: pip install openai-whisper"
            ) from exc

        self._model = whisper.load_model(self.model_name)
        return self._model

    async def transcribe_upload(self, audio_file: UploadFile) -> str:
        """Transcribe an uploaded WAV/MP3 file and return cleaned text."""
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
            text = str(result.get("text", "")).strip()
            if not text:
                raise ValueError("No speech detected in audio.")
            return " ".join(text.split())
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
