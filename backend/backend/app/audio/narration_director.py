"""
Narration Director - Orchestrates Hindi devotional narration generation.
Segments scenes, builds SSML, synthesizes per-scene audio, and concatenates.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any
from pydub import AudioSegment

from app.utils.ssml import build_hindi_ssml, segment_devotional_text
from app.audio.tts_provider import TTSProvider

logger = logging.getLogger(__name__)


def build_hindi_narration(
    plan_scenes: List[Dict[str, Any]],
    out_dir: Path,
    tts: TTSProvider
) -> Dict[str, Any]:
    """
    Build complete Hindi narration from scene plan.
    
    Args:
        plan_scenes: List of scene dicts with keys: narration, duration_sec
        out_dir: Output directory (will create voice/ subdirectory)
        tts: TTSProvider instance
    
    Returns:
        Dict with keys:
            - per_scene: List of dicts with path, duration_sec, provider, voice
            - full_narration_path: Path to concatenated voice/narration_full.wav
            - total_duration_sec: Total duration of narration
            - provider: TTS provider used
            - voice: Voice name used
            - stretch_used: Always False for now (stretch feature not implemented)
    """
    voice_dir = out_dir / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    
    per_scene = []
    scene_audio_segments = []
    provider_used = None
    voice_used = None
    
    for i, scene in enumerate(plan_scenes):
        narration_text = scene.get("narration", "")
        if not narration_text:
            logger.warning(f"Scene {i} has no narration, skipping")
            continue
        
        # Segment text into devotional phrases
        segments = segment_devotional_text(narration_text, max_chars=120)
        if not segments:
            segments = [narration_text]  # Fallback if segmentation fails
        
        # Build SSML with soothing prosody
        ssml = build_hindi_ssml(
            segments,
            rate_pct=-5,      # 5% slower for calm delivery
            pitch_semitones=-2,  # Slightly lower pitch for soothing tone
            break_ms=300      # 300ms pause between phrases
        )
        
        # Synthesize to WAV
        scene_path = voice_dir / f"scene_{i+1}.wav"
        result = tts.synthesize(
            text=narration_text,
            lang="hi",
            voice_hint="hi_female_soft",
            ssml=ssml,
            out_path=scene_path
        )
        
        per_scene.append({
            "scene_index": i + 1,
            "path": str(scene_path.relative_to(out_dir)),
            "duration_sec": result["duration_sec"],
            "provider": result["provider"],
            "voice": result["voice"]
        })
        
        if provider_used is None:
            provider_used = result["provider"]
            voice_used = result["voice"]
        
        # Load audio segment for concatenation
        audio = AudioSegment.from_wav(str(scene_path))
        scene_audio_segments.append(audio)
    
    # Concatenate all scenes into single narration file
    if scene_audio_segments:
        full_narration = scene_audio_segments[0]
        for segment in scene_audio_segments[1:]:
            full_narration += segment
        
        full_path = voice_dir / "narration_full.wav"
        full_narration.export(str(full_path), format="wav")
        total_duration = len(full_narration) / 1000.0
        
        logger.info(f"Built Hindi narration: {len(per_scene)} scenes, {total_duration:.2f}s total")
    else:
        # No narration generated
        full_path = voice_dir / "narration_full.wav"
        total_duration = 0.0
        logger.warning("No narration generated (no scenes with narration text)")
    
    return {
        "per_scene": per_scene,
        "full_narration_path": str(full_path.relative_to(out_dir)),
        "total_duration_sec": total_duration,
        "provider": provider_used or "none",
        "voice": voice_used or "none",
        "stretch_used": False  # Stretch feature not implemented yet
    }
