"""
Configuration and environment settings for DevotionalAI Platform
"""

from pydantic_settings import BaseSettings
import os
from typing import List

class Settings(BaseSettings):
    # API Settings
    API_TITLE: str = "DevotionalAI Platform"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./devocationai.db"  # Local SQLite default
    )
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://devotionalai.example.com"
    ]
    
    # Cloud Storage
    USE_S3: bool = os.getenv("USE_S3", "False") == "True"
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "devotionalai-videos")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Local Storage (fallback)
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    
    # Celery / Job Queue (memory:// for dev, redis:// for production)
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "memory://")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "")
    
    # External APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    RUNWAY_API_KEY: str = os.getenv("RUNWAY_API_KEY", "")
    # Optional mapping of friendly voice names to ElevenLabs voice IDs
    ELEVENLABS_VOICE_MAP: dict = {
        "aria": os.getenv("ELEVENLABS_VOICE_ARIA", "BZeVSRSWNw0VP88qSKp3"),
        "daya": os.getenv("ELEVENLABS_VOICE_DAYA", "MF3mGyEYCl7XYWbV7PAN")
    }
    # Replicate / HuggingFace tokens for SDXL if available
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
    
    # TTS Settings
    DEFAULT_TTS_VOICE: str = "aria"
    DEFAULT_TTS_ENGINE: str = "elevenlabs"  # elevenlabs or pyttsx3
    
    # Video Rendering
    DEFAULT_VIDEO_RESOLUTION: str = "4k"  # 720p, 1080p, 4k
    DEFAULT_VIDEO_FPS: int = 24
    DEFAULT_VIDEO_BITRATE: str = "20M"  # for 4K
    PREVIEW_VIDEO_FPS: int = 24
    PREVIEW_VIDEO_BITRATE: str = "5M"   # for previews (720p/1080p)
    
    # Image Generation
    DEFAULT_IMAGE_ENGINE: str = "openai"  # openai, sdxl, runway, local
    IMAGE_GENERATION_TIMEOUT: int = 300  # 5 minutes
    IMAGE_QUALITY: str = "4k"  # preview (720p) or final (4k)
    
    # Processing Limits
    MAX_PROJECT_SIZE_GB: float = 100.0
    MAX_VIDEO_DURATION_MINUTES: int = 60
    MAX_CONCURRENT_JOBS_PER_USER: int = 3
    JOB_TIMEOUT_MINUTES: int = 120  # 2 hours for 4K video
    
    # Safety Guardrails
    MAX_SCENES: int = int(os.getenv("MAX_SCENES", "20"))
    MAX_SCENE_DURATION_SEC: int = int(os.getenv("MAX_SCENE_DURATION_SEC", "20"))
    MAX_TOTAL_DURATION_SEC: int = int(os.getenv("MAX_TOTAL_DURATION_SEC", "600"))  # 10 min
    MAX_JOB_COST: float = float(os.getenv("MAX_JOB_COST", "50.0"))  # USD
    
    # Rate Limiting
    RATE_LIMIT_PER_MIN: int = int(os.getenv("RATE_LIMIT_PER_MIN", "10"))
    
    # Queue & Task Management
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    ENABLE_CELERY: bool = bool(REDIS_URL)
    
    # API Keys for auth
    API_KEY_ADMIN: str = os.getenv("API_KEY_ADMIN", "")
    API_KEY_CREATOR: str = os.getenv("API_KEY_CREATOR", "")
    
    # Observability
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ENABLE_SENTRY: bool = bool(SENTRY_DSN)
    JSON_LOGS: bool = os.getenv("JSON_LOGS", "true").lower() == "true"
    
    # Creator Mode: Templates & Scheduling
    SCHEDULE_TZ: str = os.getenv("SCHEDULE_TZ", "UTC")  # Timezone for scheduled publishes
    ENABLE_TEMPLATES: bool = os.getenv("ENABLE_TEMPLATES", "True") == "True"
    ENABLE_LIBRARY: bool = os.getenv("ENABLE_LIBRARY", "True") == "True"
    ENABLE_SCHEDULING: bool = os.getenv("ENABLE_SCHEDULING", "True") == "True"
    ENABLE_DUAL_SUBTITLES: bool = os.getenv("ENABLE_DUAL_SUBTITLES", "True") == "True"
    ENABLE_THUMBNAIL: bool = os.getenv("ENABLE_THUMBNAIL", "True") == "True"
    
    # YouTube API (for publishing)
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_CLIENT_ID: str = os.getenv("YOUTUBE_CLIENT_ID", "")
    YOUTUBE_CLIENT_SECRET: str = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    
    # Observability
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ENABLE_SENTRY: bool = bool(SENTRY_DSN)
    JSON_LOGS: bool = os.getenv("JSON_LOGS", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # TTS and Audio Settings
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "edge")  # edge or mock - Edge is production default
    TTS_VOICE: str = os.getenv("TTS_VOICE", "hi-IN-SwaraNeural")
    TTS_RATE: str = os.getenv("TTS_RATE", "-10%")  # Slower for soothing
    TTS_STRICT: bool = os.getenv("TTS_STRICT", "False") == "True"  # Fail render on TTS errors (True) or fallback to mock (False)
    AUDIO_PACE_TOLERANCE: float = float(os.getenv("AUDIO_PACE_TOLERANCE", "0.02"))  # Tightened to ±2%
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "24000"))
    TTS_PAUSE_MS: int = int(os.getenv("TTS_PAUSE_MS", "200"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
