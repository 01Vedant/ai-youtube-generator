from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import time


@dataclass
class Asset:
    id: str
    path: Path
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Scene:
    id: str
    prompt: str
    narration: str
    duration: float
    images: List[Asset] = field(default_factory=list)
    tts: Optional[Asset] = None
    subtitles: Optional[Asset] = None


@dataclass
class RenderJob:
    id: str
    plan: Dict[str, Any]
    output_dir: Path
    assets: List[Asset] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "pending"
    logs: List[str] = field(default_factory=list)
    durations: Dict[str, float] = field(default_factory=dict)
