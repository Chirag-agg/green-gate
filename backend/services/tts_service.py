"""Coqui TTS service for voice response synthesis."""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CoquiTTSService:
    """Generate speech audio from plain text using Coqui TTS."""

    def __init__(self) -> None:
        self.model_name_en = os.getenv("COQUI_MODEL", "tts_models/en/ljspeech/tacotron2-DDC").strip()
        self.model_name_hi = os.getenv("COQUI_HI_MODEL", self.model_name_en).strip()
        self.language = os.getenv("COQUI_LANGUAGE", "hi").strip() or "hi"
        self.output_dir = Path(
            os.getenv(
                "VOICE_OUTPUT_DIR",
                str(Path(__file__).resolve().parent.parent / "data" / "tts_outputs"),
            )
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._models: dict[str, Any] = {}

    @staticmethod
    def _has_devanagari(text: str) -> bool:
        return bool(re.search(r"[\u0900-\u097F]", text or ""))

    def _normalize_language(self, language: str | None) -> str:
        lang = (language or self.language or "").strip().lower()
        if lang in {"hi", "hindi"}:
            return "hi"
        if lang in {"en", "english"}:
            return "en"
        if lang in {"hinglish", "hi-en", "mixed"}:
            return "hinglish"
        return "auto"

    def _select_model_name(self, text: str, language: str | None) -> str:
        normalized = self._normalize_language(language)
        has_devanagari = self._has_devanagari(text)

        if normalized == "hi":
            return self.model_name_hi
        if normalized == "en":
            return self.model_name_en
        if normalized == "hinglish":
            return self.model_name_hi if has_devanagari else self.model_name_en

        # Auto mode: infer from script.
        return self.model_name_hi if has_devanagari else self.model_name_en

    def _load(self, model_name: str) -> Any:
        if model_name in self._models:
            return self._models[model_name]
        try:
            from TTS.api import TTS  # type: ignore
        except Exception as exc:
            raise RuntimeError("Coqui TTS is not installed. Install: pip install TTS") from exc

        logger.info("Loading Coqui model: %s", model_name)
        self._models[model_name] = TTS(model_name=model_name)
        return self._models[model_name]

    def _synthesize_with_gtts(self, text: str, output_path: Path, language: str) -> str:
        try:
            from gtts import gTTS  # type: ignore
        except Exception as exc:
            raise RuntimeError("gTTS is not installed. Install: pip install gTTS") from exc

        mp3_path = output_path.with_suffix(".mp3")
        tts = gTTS(text=text, lang=language)
        tts.save(str(mp3_path))
        logger.info("gTTS file generated: %s", mp3_path)
        return str(mp3_path)

    def synthesize_to_file(
        self,
        text: str,
        output_filename: str | None = None,
        language: str | None = None,
    ) -> str:
        """Convert text to speech and save WAV file, returning absolute path."""
        clean_text = " ".join(str(text or "").split())
        if not clean_text:
            raise ValueError("TTS input text is empty.")

        model_name = self._select_model_name(clean_text, language)
        model = self._load(model_name)

        if output_filename:
            filename = output_filename if output_filename.lower().endswith(".wav") else f"{output_filename}.wav"
        else:
            filename = f"output_{uuid.uuid4().hex[:10]}.wav"

        output_path = self.output_dir / filename

        normalized_lang = self._normalize_language(language)
        has_devanagari = self._has_devanagari(clean_text)

        # For Hindi/Hinglish, prefer gTTS for reliable audible output.
        if normalized_lang in {"hi", "hinglish"} or has_devanagari:
            gtts_lang = "hi" if (normalized_lang == "hi" or has_devanagari) else "en"
            try:
                return self._synthesize_with_gtts(clean_text, output_path, gtts_lang)
            except Exception as exc:
                logger.warning("gTTS synthesis failed (%s). Falling back to Coqui.", exc)

        try:
            model.tts_to_file(text=clean_text, file_path=str(output_path))
        except TypeError:
            model.tts_to_file(text=clean_text, file_path=str(output_path))
        except Exception as exc:
            logger.warning("Primary TTS synthesis failed (%s). Trying English fallback model.", exc)
            fallback_model = self._load(self.model_name_en)
            fallback_model.tts_to_file(text=clean_text, file_path=str(output_path))
        logger.info("TTS file generated: %s", output_path)
        return str(output_path)
