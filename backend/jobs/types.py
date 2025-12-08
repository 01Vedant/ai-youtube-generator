"""Plan validation via Pydantic."""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class LanguageEnum(str, Enum):
    EN = "en"
    HI = "hi"


class VoiceEnum(str, Enum):
    FEMALE = "female"
    MALE = "male"


class SceneInput(BaseModel):
    id: Optional[str] = None
    prompt: str = Field(..., description="Image generation prompt")
    narration: str = Field(..., description="Narration text for TTS")
    duration: float = Field(default=3.0, ge=1.0, le=10.0, description="Scene duration in seconds")


class RenderPlan(BaseModel):
    job_id: Optional[str] = None
    topic: Optional[str] = "Sanatan Dharma"
    language: LanguageEnum = LanguageEnum.EN
    voice: VoiceEnum = VoiceEnum.FEMALE
    length: float = Field(default=30.0, ge=10.0, le=600.0, description="Target video length in seconds")
    style: Optional[str] = "cinematic"
    scenes: List[SceneInput] = Field(..., min_items=1, max_items=20)
    images_per_scene: int = Field(default=1, ge=1, le=3)
    burn_in_subtitles: bool = False
    upload_to_cloud: bool = False
    enable_youtube_upload: bool = False
    watermark_path: Optional[str] = None
    # Hybrid pipeline flags
    enable_parallax: bool = Field(default=True, description="Enable 2.5D parallax motion")
    enable_templates: bool = Field(default=True, description="Enable motion templates")
    enable_audio_sync: bool = Field(default=True, description="Enable audio-led editing")
    quality: str = Field(default="final", description="Output quality: preview or final")

    class Config:
        use_enum_values = False
