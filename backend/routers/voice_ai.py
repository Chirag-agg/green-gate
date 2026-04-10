"""Voice AI router for a stateful, rule-based carbon data collection chatbot."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from models import User
from routers.auth import get_current_user
from services.cerebras_service import CerebrasService
from services.state_manager import StateManager, VoiceSession
from services.tts_service import CoquiTTSService
from services.validator import VoiceValidator
from services.whisper_service import WhisperService

router = APIRouter(tags=["Voice AI"])
logger = logging.getLogger(__name__)


SESSION_DATA_TEMPLATE = {
    "name": None,
    "company": None,
    "electricity_kwh": None,
    "diesel_liters": None,
    "month": None,
}


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    file_name: str | None = "output.wav"
    language: str | None = None


def _new_session(session_id: str | None = None) -> VoiceSession:
    if session_id:
        return StateManager.get_session(session_id)
    return StateManager.create_session()


def _make_response_text(session: VoiceSession) -> str:
    data = session.data or dict(SESSION_DATA_TEMPLATE)
    if session.step == "ask_name":
        return "Hi, what is your name?"
    if session.step == "ask_company":
        return "Which company are you from?"
    if session.step == "ask_electricity":
        return "Please tell me your electricity usage in units or kWh."
    if session.step == "ask_diesel":
        return "Do you use diesel? If yes, how many liters?"
    if session.step == "ask_month":
        return "Which month is this data for?"
    if session.step == "confirm":
        electricity = data.get("electricity_kwh")
        diesel = data.get("diesel_liters")
        month = data.get("month") or "unknown month"
        return (
            f"Confirming: {data.get('name')} from {data.get('company')}, electricity {electricity} kWh, "
            f"diesel {diesel} liters for {month}. Is this correct?"
        )
    if session.step == "done":
        return "Thanks. Your data has been saved."
    return "Hi, what is your name?"


def _month_from_text(text: str) -> str | None:
    lower = (text or "").lower()
    month_map = {
        "january": "January",
        "february": "February",
        "march": "March",
        "april": "April",
        "may": "May",
        "june": "June",
        "july": "July",
        "august": "August",
        "september": "September",
        "october": "October",
        "november": "November",
        "december": "December",
        "जनवरी": "January",
        "फरवरी": "February",
        "मार्च": "March",
        "अप्रैल": "April",
        "मई": "May",
        "जून": "June",
        "जुलाई": "July",
        "अगस्त": "August",
        "सितंबर": "September",
        "अक्टूबर": "October",
        "नवंबर": "November",
        "दिसंबर": "December",
    }
    for token, month in month_map.items():
        if token in lower:
            return month
    return VoiceValidator.normalize_month(text)


def _looks_like_yes(text: str) -> bool:
    return VoiceValidator.is_yes(text)


def _looks_like_no(text: str) -> bool:
    return VoiceValidator.is_no(text)


def _normalize_state(session: VoiceSession) -> VoiceSession:
    if not session.data:
        session.data = dict(SESSION_DATA_TEMPLATE)
    else:
        for key, value in SESSION_DATA_TEMPLATE.items():
            session.data.setdefault(key, value)
    return session


async def _transcribe(audio: UploadFile) -> tuple[str, str]:
    result = await WhisperService().transcribe_upload(audio)
    return result["transcript"], result.get("language", "unknown")


async def _extract_electricity(transcript: str) -> float | None:
    try:
        value = await CerebrasService().extract_electricity(transcript)
        return value
    except Exception as exc:
        logger.warning("Cerebras electricity extraction failed: %s", exc)
        return None


async def _extract_diesel(transcript: str) -> float | None:
    try:
        value = await CerebrasService().extract_diesel(transcript)
        return value
    except Exception as exc:
        logger.warning("Cerebras diesel extraction failed: %s", exc)
        return None


def _validate_and_store_number(value: float | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    if not (low <= value <= high):
        return None
    return float(value)


async def _chat_logic(session_id: str | None, transcript: str) -> dict[str, Any]:
    session = _normalize_state(_new_session(session_id))
    transcript_clean = (transcript or "").strip()
    lower = transcript_clean.lower()

    if session.step == "ask_name":
        session.data["name"] = VoiceValidator.normalize_name_or_company(transcript_clean)
        session.step = "ask_company"

    elif session.step == "ask_company":
        session.data["company"] = VoiceValidator.normalize_name_or_company(transcript_clean)
        session.step = "ask_electricity"

    elif session.step == "ask_electricity":
        value = await _extract_electricity(transcript_clean)
        value = _validate_and_store_number(value, VoiceValidator.ELECTRICITY_MIN, VoiceValidator.ELECTRICITY_MAX)
        if value is None:
            response_text = "Please tell electricity usage in units."
            audio_file = CoquiTTSService().synthesize_to_file(response_text, "output.wav", "english")
            StateManager.upsert(session)
            return {
                "transcript": transcript_clean,
                "response_text": response_text,
                "audio_file": audio_file,
                "state": session.to_dict(),
            }
        session.data["electricity_kwh"] = value
        session.step = "ask_diesel"

    elif session.step == "ask_diesel":
        if any(token in lower for token in ("skip", "no diesel", "no", "nahi", "nahin")):
            session.data["diesel_liters"] = None
            session.step = "ask_month"
        else:
            value = await _extract_diesel(transcript_clean)
            value = _validate_and_store_number(value, VoiceValidator.DIESEL_MIN, VoiceValidator.DIESEL_MAX)
            if value is None:
                response_text = "Do you use diesel? If yes, how many liters?"
                audio_file = CoquiTTSService().synthesize_to_file(response_text, "output.wav", "english")
                StateManager.upsert(session)
                return {
                    "transcript": transcript_clean,
                    "response_text": response_text,
                    "audio_file": audio_file,
                    "state": session.to_dict(),
                }
            session.data["diesel_liters"] = value
            session.step = "ask_month"

    elif session.step == "ask_month":
        month = _month_from_text(transcript_clean)
        if not month:
            response_text = "Which month is this data for?"
            audio_file = CoquiTTSService().synthesize_to_file(response_text, "output.wav", "english")
            StateManager.upsert(session)
            return {
                "transcript": transcript_clean,
                "response_text": response_text,
                "audio_file": audio_file,
                "state": session.to_dict(),
            }
        session.data["month"] = month
        session.step = "confirm"

    elif session.step == "confirm":
        if _looks_like_yes(transcript_clean):
            session.step = "done"
            response_text = "Thanks. Your data has been saved."
            audio_file = CoquiTTSService().synthesize_to_file(response_text, "output.wav", "english")
            StateManager.upsert(session)
            return {
                "transcript": transcript_clean,
                "response_text": response_text,
                "audio_file": audio_file,
                "state": session.to_dict(),
            }
        if _looks_like_no(transcript_clean):
            session = StateManager.reset(session.session_id)
            response_text = "Hi, what is your name?"
            audio_file = CoquiTTSService().synthesize_to_file(response_text, "output.wav", "english")
            return {
                "transcript": transcript_clean,
                "response_text": response_text,
                "audio_file": audio_file,
                "state": session.to_dict(),
            }
        response_text = _make_response_text(session)
        audio_file = CoquiTTSService().synthesize_to_file(response_text, "output.wav", "english")
        StateManager.upsert(session)
        return {
            "transcript": transcript_clean,
            "response_text": response_text,
            "audio_file": audio_file,
            "state": session.to_dict(),
        }

    response_text = _make_response_text(session)
    audio_language = "hindi" if any("\u0900" <= ch <= "\u097f" for ch in response_text) else "english"
    audio_file = CoquiTTSService().synthesize_to_file(response_text, "output.wav", audio_language)
    StateManager.upsert(session)

    return {
        "transcript": transcript_clean,
        "response_text": response_text,
        "audio_file": audio_file,
        "state": session.to_dict(),
    }


@router.get("/voice-health")
def voice_health() -> dict[str, Any]:
    import os

    ffmpeg_available = bool(shutil.which("ffmpeg"))
    if not ffmpeg_available:
        try:
            import imageio_ffmpeg  # type: ignore

            ffmpeg_available = bool(imageio_ffmpeg.get_ffmpeg_exe())
        except Exception:
            ffmpeg_available = False

    return {
        "status": "ok",
        "services": {
            "whisper": True,
            "ffmpeg": ffmpeg_available,
            "cerebras": bool(os.getenv("CEREBRAS_API_KEY", "").strip()),
            "tts": True,
        },
        "sessions": len(StateManager.sessions),
    }


@router.post("/chat-voice")
async def chat_voice(
    audio: UploadFile = File(...),
    session_id: str | None = Form(None),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    _ = current_user
    try:
        transcript, _language = await _transcribe(audio)
        payload = await _chat_logic(session_id, transcript)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("chat-voice failed")
        raise HTTPException(status_code=500, detail=f"Chat voice failed: {exc}") from exc


@router.post("/process-voice")
async def process_voice(
    audio: UploadFile = File(...),
    session_id: str | None = Form(None),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Backward-compatible wrapper for the stateful chatbot endpoint."""
    _ = current_user
    return await chat_voice(audio=audio, session_id=session_id)


@router.post("/tts")
def tts(payload: TTSRequest, current_user: User = Depends(get_current_user)):
    _ = current_user
    try:
        output_path = CoquiTTSService().synthesize_to_file(payload.text, payload.file_name, payload.language)
        filename = Path(output_path).name
        media_type = "audio/mpeg" if filename.lower().endswith(".mp3") else "audio/wav"
        return FileResponse(path=output_path, media_type=media_type, filename=filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {exc}") from exc


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    _ = current_user
    try:
        result = await WhisperService().transcribe_upload(audio)
        return {"transcript": result["transcript"], "language": result["language"]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
