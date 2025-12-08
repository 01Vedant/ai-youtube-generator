"""Structured error types for orchestrator failures."""
from typing import Dict, Literal, Optional


class OrchestratorError(Exception):
    """Structured exception raised during orchestrator execution."""

    code: Literal["TTS_FAILURE", "RENDER_FAILURE", "TIMEOUT", "UNKNOWN"]
    phase: Literal["init", "tts", "render", "finalize"]

    def __init__(
        self,
        message: str,
        code: Literal["TTS_FAILURE", "RENDER_FAILURE", "TIMEOUT", "UNKNOWN"],
        phase: Literal["init", "tts", "render", "finalize"],
        meta: Optional[Dict] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.phase = phase
        self.meta = meta or {}
