from pathlib import Path
import os
import uuid
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _elevenlabs_available(self):
        try:
            import elevenlabs
            return True
        except Exception:
            return False

    def generate(self, scene_id: str, text: str, voice: Optional[str] = None) -> Path:
        fname = f"{scene_id}-{uuid.uuid4().hex}.wav"
        out = self.output_dir / fname
        if os.environ.get("ELEVENLABS_API_KEY") and self._elevenlabs_available():
            try:
                from elevenlabs import generate, save
                audio = generate(text=text, voice=voice or "alloy")
                save(audio, str(out))
                return out
            except Exception as e:
                logger.warning("ElevenLabs generation failed: %s", e)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, str(out))
            engine.runAndWait()
            return out
        except Exception as e:
            logger.exception("pyttsx3 fallback failed: %s", e)
            raise
