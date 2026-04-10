"""Coqui TTS service for response speech generation."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any


class CoquiTTSService:
    """Wrapper around Coqui TTS model for WAV generation."""

    def __init__(self) -> None:
        self.model_name = os.getenv("COQUI_MODEL", "tts_models/en/ljspeech/tacotron2-DDC").strip()
        self.output_dir = Path(
            os.getenv(
                "VOICE_OUTPUT_DIR",
                str(Path(__file__).resolve().parent.parent / "data" / "tts_outputs"),
            )
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._tts_model: Any | None = None

    def _load(self) -> Any:
        if self._tts_model is not None:
            return self._tts_model

        try:
            from TTS.api import TTS  # type: ignore
        except Exception as exc:  # pragma: no cover - environment specific
            raise RuntimeError("Coqui TTS is not installed. Install with: pip install TTS") from exc

        self._tts_model = TTS(model_name=self.model_name)
        return self._tts_model

    def synthesize(self, text: str, output_filename: str | None = None) -> str:
        """Generate speech audio and return absolute file path."""
        clean_text = " ".join(str(text or "").split())
        if not clean_text:
            raise ValueError("TTS input text is empty.")

        model = self._load()

        if output_filename:
            file_name = output_filename if output_filename.lower().endswith(".wav") else f"{output_filename}.wav"
        else:
            file_name = f"voice_response_{uuid.uuid4().hex[:10]}.wav"

        output_path = self.output_dir / file_name
        model.tts_to_file(text=clean_text, file_path=str(output_path))
        return str(output_path)
