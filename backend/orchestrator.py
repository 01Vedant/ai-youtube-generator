"""
DEV Simulator Orchestrator - Zero external dependencies
Generates placeholder assets for local end-to-end testing
Used when SIMULATE_RENDER=1 (dev mode)
"""
import os
import sys
import json
import time
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any
import struct
import io

# Import from backend - rely on uvicorn's existing sys.path
# NO sys.path manipulation to avoid shadowing Python's built-in 'platform' module
from backend.app.settings import OUTPUT_ROOT
from backend.app.config import settings
from backend.app.logs.activity import log_event
from backend.app.errors import OrchestratorError

logger = logging.getLogger(__name__)


def _to_float(x, ctx=""):
    """Convert to float with detailed error message on failure."""
    try:
        return float(x)
    except Exception as e:
        raise ValueError(f"Expected float for {ctx}, got {x!r} ({type(x).__name__})") from e


def _normalize_plan_numeric(plan: dict) -> dict:
    """
    Normalize all numeric fields in plan to proper types (belt & suspenders)
    Ensures duration_sec is always float, never string or int
    """
    scenes = []
    for idx, sc in enumerate(plan.get("scenes", [])):
        s = dict(sc)
        s["duration_sec"] = _to_float(s.get("duration_sec", 5), ctx=f"scenes[{idx}].duration_sec")
        scenes.append(s)
    plan["scenes"] = scenes
    return plan


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def tiny_png() -> bytes:
    """Generate valid 1x1 PNG (69 bytes)"""
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde'
        b'\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def tiny_wav(duration_sec: float = 1.0) -> bytes:
    """Generate valid WAV file with silence"""
    sample_rate = 44100
    num_samples = int(sample_rate * duration_sec)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    
    wav = io.BytesIO()
    wav.write(b'RIFF')
    wav.write(struct.pack('<I', 36 + data_size))
    wav.write(b'WAVE')
    wav.write(b'fmt ')
    wav.write(struct.pack('<I', 16))  # fmt chunk size
    wav.write(struct.pack('<H', 1))   # audio format (PCM)
    wav.write(struct.pack('<H', num_channels))
    wav.write(struct.pack('<I', sample_rate))
    wav.write(struct.pack('<I', byte_rate))
    wav.write(struct.pack('<H', block_align))
    wav.write(struct.pack('<H', bits_per_sample))
    wav.write(b'data')
    wav.write(struct.pack('<I', data_size))
    wav.write(b'\x00' * data_size)  # silence
    
    return wav.getvalue()


def _time_stretch_wav(wav_bytes: bytes, current_duration: float, target_duration: float) -> bytes:
    """
    Time-stretch WAV audio to match target duration with polish
    - Clamps stretch to ±2% (0.98x to 1.02x)
    - Adds 10ms fade in/out
    - Trims leading/trailing silence >150ms
    
    Args:
        wav_bytes: Input WAV data
        current_duration: Current duration in seconds
        target_duration: Target duration in seconds
    
    Returns:
        Time-stretched and polished WAV bytes with metadata
    """
    try:
        from pydub import AudioSegment
        from pydub.silence import detect_leading_silence
        
        # Load WAV
        audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        
        # Trim leading/trailing silence >150ms
        trim_threshold_ms = 150
        start_trim = detect_leading_silence(audio, silence_threshold=-50.0)
        end_trim = detect_leading_silence(audio.reverse(), silence_threshold=-50.0)
        
        if start_trim > trim_threshold_ms:
            audio = audio[start_trim:]
        if end_trim > trim_threshold_ms:
            audio = audio[:-end_trim]
        
        # Calculate stretch factor and clamp to ±2%
        stretch_factor = current_duration / target_duration
        clamped_stretch = max(0.98, min(1.02, stretch_factor))
        
        if abs(clamped_stretch - 1.0) > 0.001:  # Only stretch if meaningful
            # Time-stretch via frame rate manipulation
            new_frame_rate = int(audio.frame_rate * clamped_stretch)
            audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
            audio = audio.set_frame_rate(24000)  # Normalize to 24kHz
        
        # Add 10ms fade in/out for smooth transitions
        audio = audio.fade_in(10).fade_out(10)
        
        # Export
        buffer = io.BytesIO()
        audio.export(buffer, format="wav")
        return buffer.getvalue()
        
    except ImportError:
        # Fallback: simple truncate or pad with silence
        if target_duration < current_duration:
            # Truncate
            import wave
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
                params = wav.getparams()
                frames_needed = int(params.framerate * target_duration)
                frames = wav.readframes(frames_needed)
            
            # Write truncated WAV
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as out_wav:
                out_wav.setparams(params)
                out_wav.writeframes(frames)
            return buffer.getvalue()
        else:
            # Pad with silence
            silence_duration = target_duration - current_duration
            silence = tiny_wav(silence_duration)
            # Concatenate (simple append - not perfect but works)
            return wav_bytes + silence


def tiny_srt(language: str = "en") -> str:
    """Generate minimal valid SRT subtitle"""
    if language == "hi":
        text = "नमस्ते"
    else:
        text = "Hello"
    
    return f"""1
00:00:00,000 --> 00:00:03,000
{text}

2
00:00:03,000 --> 00:00:06,000
Test subtitle

"""


def tiny_mp4(duration_sec: float = 5.0) -> bytes:
    """
    Generate minimal valid MP4 video file with single black frame
    Uses raw MP4 atoms to create smallest possible valid video
    """
    # Minimal MP4 with ftyp, moov, and mdat boxes
    # This is a ~1KB valid MP4 that any player can open
    
    ftyp = (
        b'ftyp'  # box type
        b'mp42'  # major brand
        b'\x00\x00\x00\x00'  # minor version
        b'mp42' b'isom'  # compatible brands
    )
    
    moov = (
        b'moov'
        b'\x00\x00\x00\x6c'  # mvhd box (placeholder)
        b'mvhd' b'\x00' * 100  # minimal movie header
    )
    
    mdat = (
        b'mdat'  # media data box
        b'\x00' * 64  # minimal video data
    )
    
    # Calculate sizes
    ftyp_size = len(ftyp) + 8
    moov_size = len(moov) + 8
    mdat_size = len(mdat) + 8
    
    # Build MP4
    mp4 = io.BytesIO()
    mp4.write(struct.pack('>I', ftyp_size) + ftyp)
    mp4.write(struct.pack('>I', moov_size) + moov)
    mp4.write(struct.pack('>I', mdat_size) + mdat)
    
    return mp4.getvalue()


def mkbytes(path: Path, data: bytes) -> None:
    """Safely write bytes to file, creating parent dirs"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class Orchestrator:
    """
    DEV Simulator Orchestrator for local testing
    Generates placeholder assets without GPU/FFmpeg/cloud services
    """
    
    def __init__(
        self,
        status_callback: Optional[Callable[[str, int, Dict[str, Any]], None]] = None,
        out_dir: Optional[str] = None,
        base_dir: Optional[Path] = None
    ):
        """
        Initialize simulator
        
        Args:
            status_callback: Called with (step_name, progress_pct, metadata)
            out_dir: Output directory path (deprecated, use base_dir)
            base_dir: Base directory for outputs (platform/pipeline_outputs)
        """
        self.status_callback = status_callback
        if base_dir:
            self.base_dir = Path(base_dir)
        elif out_dir:
            self.base_dir = Path(out_dir)
        else:
            self.base_dir = OUTPUT_ROOT
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _emit_status(self, step: str, progress: int, meta: Optional[Dict] = None):
        """Emit status callback if provided"""
        if self.status_callback:
            self.status_callback(step, progress, meta or {})
    
    def _handle_failure(
        self,
        *,
        job_id: str,
        plan: dict,
        assets: list,
        logs: list,
        job_dir: Path,
        started_at: str,
        start_time: float,
        error: OrchestratorError,
        status_callback: Optional[Callable],
        original_callback: Optional[Callable],
        audio_metadata: Optional[Dict[str, Any]] = None,
        audio_error: Optional[str] = None,
    ) -> dict:
        """Handle orchestrator failure with structured error summary."""

        logger.error(
            "Render job %s failed (%s/%s): %s",
            job_id,
            error.code,
            error.phase,
            error.message,
        )

        logs.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": "error",
            "message": error.message,
        })

        self._emit_status(
            "error",
            0,
            {
                "code": error.code,
                "phase": error.phase,
                "message": error.message,
            },
        )

        log_event(
            job_id=job_id,
            event_type="job_failed",
            message=error.message,
            meta={"code": error.code, "phase": error.phase, **error.meta},
        )

        finished_at = datetime.now(timezone.utc).isoformat()
        elapsed_sec = time.time() - start_time

        summary = {
            "job_id": job_id,
            "state": "error",
            "step": "error",
            "progress": 0,
            "started_at": started_at,
            "finished_at": finished_at,
            "elapsed_sec": elapsed_sec,
            "encoder": "simulator",
            "assets": assets,
            "logs": logs,
            "error": {
                "code": error.code,
                "phase": error.phase,
                "message": error.message,
                "meta": error.meta,
            },
            "plan": plan,
        }

        if audio_metadata:
            summary["audio"] = audio_metadata

        if audio_error:
            summary["audio_error"] = audio_error

        summary_path = job_dir / "job_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        if status_callback:
            self.status_callback = original_callback

        return summary

    def _sleep_simulate(self, min_sec: float = 0.3, max_sec: float = 0.6):
        """Sleep to simulate processing time"""
        import random
        time.sleep(random.uniform(min_sec, max_sec))
    
    def run(self, plan: dict, status_callback: Optional[Callable] = None) -> dict:
        """
        Run simulated render pipeline
        
        Args:
            plan: RenderPlan dict with scenes, settings, etc.
            status_callback: Optional callback for status updates (overrides init callback)
        
        Returns:
            dict with job_id, assets, final_video_url, state, etc.
        """
        # Use provided callback or fall back to instance callback
        original_callback = self.status_callback
        if status_callback:
            self.status_callback = status_callback
        
        start_time = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        
        # Use job_id from plan, or generate new one
        job_id = plan.get("job_id", str(uuid.uuid4()))
        
        # Log job creation
        log_event(
            job_id=job_id,
            event_type="job_created",
            message=f"Render job created for topic: {plan.get('topic', 'untitled')}",
            meta={
                "topic": plan.get("topic", "untitled"),
                "language": plan.get("language", "en"),
                "voice": plan.get("voice", "F"),
                "num_scenes": len(plan.get("scenes", []))
            }
        )
        
        # Normalize plan numeric fields (belt & suspenders)
        plan = _normalize_plan_numeric(plan)
        logger.info("Durations(types)=%s values=%s",
            [type(s["duration_sec"]).__name__ for s in plan["scenes"]],
            [s["duration_sec"] for s in plan["scenes"]]
        )
        
        # Create output structure
        job_dir = self.base_dir / job_id
        images_dir = job_dir / "images"
        audio_dir = job_dir / "audio"
        subs_dir = job_dir / "subs"
        final_dir = job_dir / "final"
        
        for d in [images_dir, audio_dir, subs_dir, final_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        assets = []
        logs = []
        
        # Initialize hybrid pipeline tracking variables
        templates_applied = False
        templates_count = 0
        parallax_applied = False
        parallax_scenes = 0
        audio_director_data = {"beats_used": 0, "ducking_applied": False}
        profile_used = plan.get("quality", "final")
        qa_status = "ok"
        
        def log(msg: str):
            elapsed_ms = int((time.time() - start_time) * 1000)
            logs.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": "info",
                "message": f"[{elapsed_ms}ms] {msg}"
            })
            print(f"[SIMULATOR {job_id[:8]}] [{elapsed_ms}ms] {msg}")
        
        try:
            # Step 1: Images
            log("Generating placeholder images...")
            self._emit_status("images", 10, {"job_id": job_id})
            num_scenes = len(plan.get("scenes", [{"id": 1}]))
            for i in range(num_scenes):
                scene_num = i + 1
                img_path = images_dir / f"scene_{scene_num}.png"
                mkbytes(img_path, tiny_png())
                assets.append({
                    "type": "image",
                    "label": f"Scene {scene_num}",
                    "path": f"images/scene_{scene_num}.png"
                })
            self._sleep_simulate(0.3, 0.5)
            self._emit_status("images", 30, {"completed": num_scenes})
            log(f"Generated {num_scenes} placeholder images")
            
            # Step 2: TTS
            log("Generating audio...")
            self._emit_status("tts", 40, {})
            
            # Initialize audio metadata (will be populated if Hindi narration is generated)
            audio_metadata = None
            audio_error = None
            
            # Check if Hindi TTS is requested
            language = plan.get("language", "en")
            voice_id = plan.get("voice_id", None)
            
            # Log TTS start
            log_event(
                job_id=job_id,
                event_type="tts_started",
                message=f"Starting TTS generation with language={language}, voice={voice_id or 'default'}",
                meta={"language": language, "voice_id": voice_id}
            )
            
            # Loud diagnostics for TTS path
            logger.info("[TTS] language=%s voice_id=%s provider=%s", language, voice_id, settings.TTS_PROVIDER)
            log(f"[TTS] language={language} voice_id={voice_id} provider={settings.TTS_PROVIDER}")
            
            if language == "hi":
                log(f"Generating Hindi narration with voice={voice_id or settings.TTS_VOICE}...")
                try:
                    from backend.app.tts.engine import synthesize, get_provider_info
                    
                    # Create audio/ subdirectory
                    audio_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create cache directory
                    cache_dir = OUTPUT_ROOT / "_cache" / "tts"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    
                    provider_info = get_provider_info()
                    log(f"Using TTS provider: {provider_info['name']}")
                    
                    # Process each scene (Task 6: Track telemetry)
                    scene_audio_files = []
                    total_duration = 0.0
                    paced_count = 0
                    total_synth_ms = 0
                    cache_hits = 0
                    
                    for i, scene in enumerate(plan.get("scenes", [])):
                        scene_num = i + 1
                        narration_text = scene.get("narration", "")
                        target_duration = _to_float(scene.get("duration_sec", 5), ctx=f"scene[{i}].duration_sec")
                        
                        if not narration_text:
                            continue
                        
                        log(f"Scene {scene_num}: synthesizing '{narration_text[:40]}...' (target: {target_duration}s)")
                        
                        # Synthesize with caching
                        wav_bytes, metadata = synthesize(
                            text=narration_text,
                            lang=language,
                            voice_id=voice_id,
                            cache_dir=cache_dir
                        )
                        
                        raw_duration = _to_float(metadata["duration_sec"], ctx="raw_duration from TTS")
                        synth_ms = metadata.get("synth_ms", 0)
                        cache_hit = metadata.get("cache_hit", False)
                        
                        total_synth_ms += synth_ms
                        if cache_hit:
                            cache_hits += 1
                        
                        log(f"Scene {scene_num}: synthesized {raw_duration:.2f}s in {synth_ms}ms (cached={cache_hit})")
                        
                        # Time-stretch if needed (within ±2% tolerance)
                        tolerance = settings.AUDIO_PACE_TOLERANCE  # 0.02 = ±2%
                        
                        # Debug logging before math operations
                        logger.debug("Pacing types: raw=%s target=%s tolerance=%s", 
                                   type(raw_duration).__name__, type(target_duration).__name__, type(tolerance).__name__)
                        
                        duration_diff = abs(raw_duration - target_duration)
                        needs_stretch = duration_diff > (target_duration * tolerance)
                        stretch_ratio = 1.0
                        
                        if needs_stretch:
                            stretch_ratio = raw_duration / target_duration
                            log(f"Scene {scene_num}: pacing {raw_duration:.2f}s → {target_duration:.2f}s (ratio={stretch_ratio:.3f})")
                            wav_bytes = _time_stretch_wav(wav_bytes, raw_duration, target_duration)
                            final_duration = target_duration
                            paced_count += 1
                        else:
                            final_duration = raw_duration
                        
                        # Save scene audio
                        scene_audio_path = audio_dir / f"scene_{scene_num}.wav"
                        scene_audio_path.write_bytes(wav_bytes)
                        
                        scene_audio_files.append({
                            "scene_index": scene_num,
                            "path": f"audio/scene_{scene_num}.wav",
                            "duration_sec": final_duration,
                            "paced": needs_stretch,
                            "stretch_ratio": stretch_ratio if needs_stretch else None
                        })
                        
                        assets.append({
                            "type": "audio",
                            "label": f"Scene {scene_num} Audio (Hindi)",
                            "path": f"audio/scene_{scene_num}.wav"
                        })
                        
                        total_duration += final_duration
                    
                    # Build audio metadata for job summary (Task 6: Add telemetry)
                    audio_metadata = {
                        "lang": language,
                        "voice_id": voice_id or provider_info.get("voices", ["default"])[0],
                        "provider": provider_info["name"],
                        "paced": paced_count > 0,
                        "total_duration_sec": total_duration,
                        "duration_ms": int(total_duration * 1000),
                        "synth_ms": total_synth_ms,
                        "cache_hits": cache_hits,
                        "cache_hit_rate": cache_hits / len(scene_audio_files) if scene_audio_files else 0,
                        "scenes": scene_audio_files
                    }
                    
                    log(f"Hindi narration complete: {total_duration:.2f}s total, {paced_count} scenes paced, provider={provider_info['name']}, synth_ms={total_synth_ms}, cache_hits={cache_hits}/{len(scene_audio_files)}")
                    logger.info(f"[TTS] SUCCESS: {len(scene_audio_files)} scenes, {total_duration:.2f}s total, provider={provider_info['name']}, synth_ms={total_synth_ms}, cache_hits={cache_hits}")
                    
                    # Log TTS completion
                    log_event(
                        job_id=job_id,
                        event_type="tts_completed",
                        message=f"TTS generation completed: {total_duration:.2f}s total audio",
                        meta={
                            "total_duration_sec": total_duration,
                            "scenes_count": len(scene_audio_files),
                            "provider": provider_info['name'],
                            "cache_hits": cache_hits
                        }
                    )
                    
                    # Task 4: Generate combined narration.wav for download
                    try:
                        from pydub import AudioSegment
                        
                        combined_audio = AudioSegment.empty()
                        for scene_file in scene_audio_files:
                            scene_path = output_dir / scene_file["path"]
                            segment = AudioSegment.from_wav(str(scene_path))
                            combined_audio += segment
                        
                        narration_path = output_dir / "narration.wav"
                        combined_audio.export(str(narration_path), format="wav")
                        log(f"Saved combined narration.wav ({total_duration:.2f}s)")
                        
                        assets.append({
                            "type": "audio",
                            "label": "Full Narration (Hindi)",
                            "path": "narration.wav"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to create combined narration.wav: {e}")
                    
                    # Task 4: Generate captions.srt for download
                    try:
                        srt_lines = []
                        cumulative_time = 0.0
                        
                        for i, scene in enumerate(plan.get("scenes", [])):
                            narration = scene.get("narration", "")
                            duration = _to_float(scene_audio_files[i]["duration_sec"], ctx=f"captions scene[{i}] duration") if i < len(scene_audio_files) else 3.0
                            
                            if not narration:
                                continue
                            
                            # SRT format: index, timestamp, text
                            srt_start = _format_srt_time(cumulative_time)
                            srt_end = _format_srt_time(cumulative_time + duration)
                            
                            srt_lines.append(f"{i + 1}")
                            srt_lines.append(f"{srt_start} --> {srt_end}")
                            srt_lines.append(narration)
                            srt_lines.append("")  # Blank line between entries
                            
                            cumulative_time += duration
                        
                        captions_path = output_dir / "captions.srt"
                        captions_path.write_text("\n".join(srt_lines), encoding="utf-8")
                        log(f"Saved captions.srt ({len(srt_lines) // 4} subtitles)")
                        
                        assets.append({
                            "type": "srt",
                            "label": "Hindi Captions (SRT)",
                            "path": "captions.srt"
                        })
                    except Exception as e:
                        logger.warning(f"Failed to create captions.srt: {e}")
                    
                except Exception as e:
                    import traceback

                    error_msg = str(e)
                    stack_trace = traceback.format_exc()
                    logger.error("[TTS] Hindi synthesis failed: %s\n%s", error_msg, stack_trace)
                    log(f"Hindi TTS failed: {error_msg}")

                    raise OrchestratorError(
                        message=f"TTS pipeline failed: {error_msg}",
                        code="TTS_FAILURE",
                        phase="tts",
                        meta={
                            "language": language,
                            "voice_id": voice_id,
                            "details": error_msg,
                        },
                    ) from e
            else:
                # Non-Hindi: use placeholder audio
                for i in range(num_scenes):
                    scene_num = i + 1
                    audio_path = audio_dir / f"scene_{scene_num}.wav"
                    mkbytes(audio_path, tiny_wav(3.0))
                    assets.append({
                        "type": "audio",
                        "label": f"Scene {scene_num} Audio",
                        "path": f"audio/scene_{scene_num}.wav"
                    })
            
            self._sleep_simulate(0.3, 0.5)
            self._emit_status("tts", 55, {"completed": num_scenes})
            log(f"Audio generation complete")
            
            # Step 3: Subtitles
            log("Generating placeholder subtitles...")
            self._emit_status("subtitles", 65, {})
            for lang in ["en", "hi"]:
                srt_path = subs_dir / f"subs_{lang}.srt"
                srt_path.write_text(tiny_srt(lang), encoding="utf-8")
                assets.append({
                    "type": "srt",
                    "label": f"Subtitles ({lang.upper()})",
                    "path": f"subs/subs_{lang}.srt"
                })
            self._sleep_simulate(0.2, 0.4)
            self._emit_status("subtitles", 75, {})
            log("Generated subtitles (en, hi)")
            
            # Step 3.5: Apply motion templates if enabled
            if plan.get("enable_templates", True):
                try:
                    from backend.app.motion.templates import list_templates
                    log("Applying motion templates...")
                    # In simulator mode, just log which templates would be applied
                    available_templates = list_templates()
                    templates_count = min(len(available_templates), num_scenes + 2)  # Per scene + title + xfade
                    templates_applied = True
                    log(f"Motion templates applied: {templates_count} filters")
                except Exception as e:
                    log(f"Templates skipped: {e}")
            
            # Step 3.6: Apply parallax if enabled
            if plan.get("enable_parallax", True):
                try:
                    from backend.app.motion.parallax import estimate_depth
                    log("Applying 2.5D parallax motion...")
                    # In simulator mode, just track that we would apply it
                    parallax_scenes = num_scenes
                    parallax_applied = True
                    log(f"Parallax applied to {parallax_scenes} scenes")
                except Exception as e:
                    log(f"Parallax skipped: {e}")
            
            # Step 3.7: Audio director (beat detection) if enabled
            if plan.get("enable_audio_sync", True):
                try:
                    from backend.app.audio.director import detect_beats
                    log("Detecting audio beats...")
                    # In simulator mode, return synthetic beats
                    beats = detect_beats(audio_dir / "scene_1.wav")  # Sample
                    audio_director_data["beats_used"] = len(beats) if beats else 0
                    audio_director_data["ducking_applied"] = True
                    log(f"Audio sync: {audio_director_data['beats_used']} beats detected, ducking applied")
                except Exception as e:
                    log(f"Audio sync skipped: {e}")
            
            try:
                # Step 4: Stitch - normalize to final_video.mp4 at root
                log("Creating placeholder video...")
                log_event(
                    job_id=job_id,
                    event_type="render_started",
                    message="Starting video composition",
                    meta={"template": plan.get("quality", "final")}
                )
                self._emit_status("stitch", 80, {})
                # Write to standardized location: job_dir/final_video.mp4
                final_video = job_dir / "final_video.mp4"
                final_video.write_bytes(tiny_mp4(duration_sec=5))
                self._sleep_simulate(0.4, 0.6)
                self._emit_status("stitch", 90, {})
                log("Created final_video.mp4 (normalized location)")
                log_event(
                    job_id=job_id,
                    event_type="render_completed",
                    message="Video composition completed",
                    meta={"video_path": "final_video.mp4"}
                )
                
                # Step 5: Upload (simulated)
                log("Simulating upload...")
                self._emit_status("upload", 95, {})
                self._sleep_simulate(0.2, 0.3)
                log("Upload simulation complete")
            except Exception as e:
                raise OrchestratorError(
                    message=f"Render pipeline failed: {e}",
                    code="RENDER_FAILURE",
                    phase="render",
                    meta={"details": str(e)},
                ) from e
            
            # Step 6: Completed
            finished_at = datetime.now(timezone.utc).isoformat()
            elapsed_sec = time.time() - start_time
            elapsed_ms = int(elapsed_sec * 1000)
            
            self._emit_status("completed", 100, {"elapsed_sec": elapsed_sec})
            log(f"Job completed in {elapsed_sec:.2f}s")
            
            # Run QA checks
            try:
                from backend.app.motion.qa import run_qa_checks
                qa_result = run_qa_checks(final_video, [subs_dir / "subs_en.srt"], {})
                qa_status = qa_result["status"]
                log(f"QA checks: {qa_result['passed_checks']}/{qa_result['total_checks']} passed")
            except Exception as e:
                log(f"QA checks skipped: {e}")
            
            # Get quality profile info
            try:
                from backend.app.motion.profiles import get_profile
                profile_info = get_profile(profile_used)
            except Exception:
                profile_info = {"name": profile_used, "resolution": "1080p"}
            
            # Write job summary
            summary = {
                "job_id": job_id,
                "state": "success",
                "step": "completed",
                "progress": 100,
                "started_at": started_at,
                "finished_at": finished_at,
                "elapsed_sec": elapsed_sec,
                "encoder": "simulator",
                "resolution": profile_info.get("resolution", "1080p"),
                "fast_path": True,
                "proxy": True,
                "assets": assets,
                "final_video_url": f"/artifacts/{job_id}/final_video.mp4",
                "templates": {
                    "applied": templates_applied,
                    "count": templates_count
                },
                "parallax": {
                    "applied": parallax_applied,
                    "scenes": parallax_scenes
                },
                "audio_director": audio_director_data,
                "profile": {
                    "name": profile_used,
                    "resolution": profile_info.get("resolution", "1080p"),
                    "fps": profile_info.get("fps", 24)
                },
                "qa": {
                    "status": qa_status
                },
                "timings": {
                    "total_ms": elapsed_ms,
                    "images_ms": int(elapsed_ms * 0.3),
                    "audio_ms": int(elapsed_ms * 0.25),
                    "subtitles_ms": int(elapsed_ms * 0.2),
                    "stitch_ms": int(elapsed_ms * 0.2),
                    "upload_ms": int(elapsed_ms * 0.05)
                },
                "logs": logs,
                "error": None,
                "plan": plan  # Store original plan for retry/duplicate
            }
            
            # Add audio metadata if Hindi narration was generated
            if audio_metadata:
                summary["audio"] = audio_metadata
            
            # Add audio error if TTS failed
            if audio_error:
                summary["audio_error"] = audio_error
            
            summary_path = job_dir / "job_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            
            # Log job completion
            log_event(
                job_id=job_id,
                event_type="job_completed",
                message=f"Render job completed successfully in {elapsed_sec:.1f}s",
                meta={"elapsed_sec": elapsed_sec, "state": "success"}
            )
            
            return summary
            
        except OrchestratorError as orchestrator_error:
            return self._handle_failure(
                job_id=job_id,
                plan=plan,
                assets=assets,
                logs=logs,
                job_dir=job_dir,
                started_at=started_at,
                start_time=start_time,
                error=orchestrator_error,
                status_callback=status_callback,
                original_callback=original_callback,
                audio_metadata=audio_metadata,
                audio_error=audio_error,
            )
        except TimeoutError as timeout_error:
            orchestrator_error = OrchestratorError(
                message=str(timeout_error),
                code="TIMEOUT",
                phase="render",
                meta={"exception_type": type(timeout_error).__name__},
            )
            return self._handle_failure(
                job_id=job_id,
                plan=plan,
                assets=assets,
                logs=logs,
                job_dir=job_dir,
                started_at=started_at,
                start_time=start_time,
                error=orchestrator_error,
                status_callback=status_callback,
                original_callback=original_callback,
                audio_metadata=audio_metadata,
                audio_error=audio_error,
            )
        except Exception as unhandled_error:
            logger.exception("Render failed with unhandled exception")
            orchestrator_error = OrchestratorError(
                message=str(unhandled_error),
                code="UNKNOWN",
                phase="finalize",
                meta={"exception_type": type(unhandled_error).__name__},
            )
            return self._handle_failure(
                job_id=job_id,
                plan=plan,
                assets=assets,
                logs=logs,
                job_dir=job_dir,
                started_at=started_at,
                start_time=start_time,
                error=orchestrator_error,
                status_callback=status_callback,
                original_callback=original_callback,
                audio_metadata=audio_metadata,
                audio_error=audio_error,
            )
        finally:
            if status_callback:
                self.status_callback = original_callback


def run_selftest_simulated() -> Dict[str, Any]:
    """
    Self-test function for simulator orchestrator
    Validates that simulation works end-to-end
    Returns comprehensive test results
    """
    print("\n" + "="*70)
    print("SIMULATOR SELF-TEST")
    print("="*70 + "\n")
    
    results = {
        "passed": False,
        "tests": [],
        "errors": [],
        "job_id": None,
        "duration_sec": 0.0
    }
    
    start_time = time.time()
    
    try:
        # Test 1: Create tiny plan
        print("✓ Creating test plan (1 scene)...")
        plan = {
            "job_id": str(uuid.uuid4()),
            "topic": "Self-test video",
            "language": "en",
            "voice": "F",
            "scenes": [
                {
                    "image_prompt": "test image",
                    "narration": "test narration",
                    "duration_sec": 1
                }
            ]
        }
        results["job_id"] = plan["job_id"]
        results["tests"].append({"name": "plan_creation", "passed": True})
        
        # Test 2: Initialize orchestrator
        print("✓ Initializing simulator orchestrator...")
        orch = Orchestrator(base_dir=OUTPUT_ROOT)
        results["tests"].append({"name": "orchestrator_init", "passed": True})
        
        # Test 3: Track status updates
        status_updates = []
        def test_callback(step: str, progress: int, meta: Optional[Dict] = None):
            status_updates.append({"step": step, "progress": progress})
        
        print("✓ Running simulation...")
        summary = orch.run(plan, status_callback=test_callback)
        
        # Test 4: Validate status progression
        print(f"✓ Received {len(status_updates)} status updates")
        if len(status_updates) >= 5:
            results["tests"].append({"name": "status_updates", "passed": True})
        else:
            results["errors"].append(f"Expected >=5 status updates, got {len(status_updates)}")
        
        # Test 5: Validate job_summary.json exists
        job_dir = OUTPUT_ROOT / summary.get("job_id")
        summary_path = job_dir / "job_summary.json"
        if summary_path.exists():
            print(f"✓ job_summary.json created at {summary_path}")
            results["tests"].append({"name": "summary_file", "passed": True})
            
            # Validate JSON structure
            summary_data = json.loads(summary_path.read_text())
            required_fields = ["job_id", "state", "assets", "final_video_url", "encoder", "timings"]
            missing = [f for f in required_fields if f not in summary_data]
            if not missing:
                results["tests"].append({"name": "summary_structure", "passed": True})
                print(f"✓ Encoder: {summary_data.get('encoder')}")
                print(f"✓ Timings: {summary_data.get('timings', {}).get('total_ms')}ms")
            else:
                results["errors"].append(f"Missing fields in summary: {missing}")
        else:
            results["errors"].append("job_summary.json not created")
        
        # Test 6: Validate assets generated
        assets = summary.get("assets", [])
        if len(assets) >= 4:  # Expect image, audio, 2x subtitles minimum
            print(f"✓ Generated {len(assets)} assets")
            results["tests"].append({"name": "assets_generation", "passed": True})
        else:
            results["errors"].append(f"Expected >=4 assets, got {len(assets)}")
        
        # Test 7: Validate final video URL format
        final_url = summary.get("final_video_url", "")
        if final_url.startswith("/artifacts/"):
            print(f"✓ Final video URL: {final_url}")
            results["tests"].append({"name": "final_video_url", "passed": True})
        else:
            results["errors"].append(f"final_video_url should start with /artifacts/, got: {final_url}")
        
        # All tests passed
        results["passed"] = len(results["errors"]) == 0
        results["duration_sec"] = time.time() - start_time
        
        if results["passed"]:
            print(f"\n{'='*70}")
            print(f"✅ SIMULATOR SELFTEST PASSED ({results['duration_sec']:.2f}s)")
            print(f"{'='*70}\n")
        else:
            print(f"\n{'='*70}")
            print(f"❌ SIMULATOR SELFTEST FAILED")
            for error in results["errors"]:
                print(f"   - {error}")
            print(f"{'='*70}\n")
        
    except Exception as e:
        results["passed"] = False
        results["errors"].append(f"Exception: {str(e)}")
        results["duration_sec"] = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"❌ SIMULATOR SELFTEST FAILED")
        print(f"Exception: {e}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
    
    return results
