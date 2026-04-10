"""In-memory conversation state manager for the voice chatbot."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
from uuid import uuid4


VOICE_STEPS = (
    "ask_name",
    "ask_company",
    "ask_electricity",
    "ask_diesel",
    "ask_month",
    "confirm",
    "done",
)


@dataclass
class VoiceSession:
    session_id: str
    step: str = "ask_name"
    data: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.data is None:
            self.data = {
                "name": None,
                "company": None,
                "electricity_kwh": None,
                "diesel_liters": None,
                "month": None,
            }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StateManager:
    """Stores voice sessions in global memory."""

    sessions: dict[str, VoiceSession] = {}

    @classmethod
    def create_session(cls, session_id: str | None = None) -> VoiceSession:
        session = VoiceSession(session_id=session_id or uuid4().hex)
        cls.sessions[session.session_id] = session
        return session

    @classmethod
    def get_session(cls, session_id: str | None) -> VoiceSession:
        if session_id:
            if session_id in cls.sessions:
                return cls.sessions[session_id]
            session = cls.create_session(session_id)
            return session
        session = cls.create_session()
        return session

    @classmethod
    def upsert(cls, session: VoiceSession) -> VoiceSession:
        cls.sessions[session.session_id] = session
        return session

    @classmethod
    def reset(cls, session_id: str) -> VoiceSession:
        session = VoiceSession(session_id=session_id)
        cls.sessions[session_id] = session
        return session
