"""
Video Renderer: assembles final MP4 from images + audio + optional watermark.
Supports two rendering paths:
1. FAST_PATH (default): GPU-accelerated FFmpeg with NVENC, scene caching, VBR encoding
2. FALLBACK: MoviePy-based simple rendering
"""
from pathlib import Path
import logging
import os
import json
import hashlib
import subprocess
import time
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
from typing import List, Optional, Dict, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class VideoRenderer:
    def __init__(self, output_dir: Path, fps: int = 24):
        self.output_dir = Path(output_dir)
        self.fps = fps
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.nvenc_available = self._check_nvenc_available()
        
    def _check_nvenc_available(self) -> bool:
        """Check if NVENC hardware encoder is available via ffmpeg."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "h264_nvenc" in result.stdout or "hevc_nvenc" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def _get_scene_hash(self, image_path: str, narration: str, duration: float) -> str:
        """Generate deterministic hash for scene caching."""
        data = f"{image_path}|{narration}|{duration}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _render_scene_fastpath(
        self,
        scene_idx: int,
        image_path: str,
        duration: float,
        scene_hash: str,
        tmp_dir: Path,
        encoder: str,
        target_res: str,
        render_mode: str,
        cq: int,
        vbr_target: str,
        maxrate: str,
        bufsize: str
    ) -> Tuple[str, float]:
        """
        Render a single scene to MP4 using FFmpeg with GPU acceleration.
        Returns (output_path, render_time).
        """
        start_time = time.time()
        output_path = tmp_dir / f"scene_{scene_idx:03d}_{scene_hash}.mp4"
        
        # Check cache
        if output_path.exists():
            render_time = time.time() - start_time
            logger.info(f"Scene {scene_idx} cache hit, skipping render")
            return (str(output_path), render_time)
        
        # Parse target resolution
        res_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "4k": (3840, 2160)
        }
        width, height = res_map.get(target_res, (1920, 1080))
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-t", str(duration),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fade=t=in:st=0:d=0.5,fade=t=out:st={duration-0.5}:d=0.5",
            "-c:v", encoder
        ]
        
        # Add encoder-specific flags
        if "nvenc" in encoder:
            if render_mode == "PROXY":
                cmd.extend(["-preset", "fast", "-rc:v", "vbr", "-cq:v", str(cq + 5)])
            else:  # FINAL
                cmd.extend(["-preset", "slow", "-rc:v", "vbr", "-cq:v", str(cq), "-b:v", vbr_target, "-maxrate:v", maxrate, "-bufsize", bufsize])
        else:  # libx264 fallback
            if render_mode == "PROXY":
                cmd.extend(["-preset", "ultrafast", "-crf", str(cq + 5)])
            else:  # FINAL
                cmd.extend(["-preset", "slow", "-crf", str(cq)])
        
        cmd.extend(["-r", str(self.fps), "-pix_fmt", "yuv420p", str(output_path)])
        
        # Execute
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Scene {scene_idx} rendered in {time.time() - start_time:.2f}s")
        except subprocess.CalledProcessError as e:
            logger.error(f"Scene {scene_idx} render failed: {e.stderr.decode()}")
            raise
        
        render_time = time.time() - start_time
        return (str(output_path), render_time)
    
    def _concat_scenes_fastpath(
        self,
        scene_paths: List[str],
        audio_path: Optional[str],
        watermark_path: Optional[str],
        subtitle_path: Optional[str],
        output_path: Path,
        encoder: str,
        render_mode: str,
        cq: int,
        vbr_target: str,
        maxrate: str,
        bufsize: str,
        music_db: int,
        watermark_pos: str,
        tmp_dir: Path
    ) -> float:
        """
        Concatenate scene clips with audio, watermark, and subtitles using FFmpeg filter_complex.
        Returns render time in seconds.
        """
        start_time = time.time()
        
        # Create concat.txt for scene concatenation
        concat_file = tmp_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for scene_path in scene_paths:
                f.write(f"file '{scene_path}'\n")
        
        # Build FFmpeg command
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file)]
        
        # Add audio if present
        filter_parts = []
        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-i", audio_path])
            filter_parts.append(f"[1:a]volume={music_db}dB[aud]")
        
        # Add watermark if present
        if watermark_path and os.path.exists(watermark_path):
            cmd.extend(["-i", watermark_path])
            pos_map = {
                "tl": "10:10",
                "tr": "W-w-10:10",
                "bl": "10:H-h-10",
                "br": "W-w-10:H-h-10"
            }
            watermark_filter = f"[0:v][2:v]overlay={pos_map.get(watermark_pos, 'W-w-10:H-h-10')}[vout]"
            filter_parts.append(watermark_filter)
        else:
            filter_parts.append("[0:v]copy[vout]")
        
        # Combine filters
        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts)])
            cmd.extend(["-map", "[vout]"])
            if audio_path:
                cmd.extend(["-map", "[aud]"])
        
        # Add video encoding options
        cmd.extend(["-c:v", encoder])
        if "nvenc" in encoder:
            if render_mode == "PROXY":
                cmd.extend(["-preset", "fast", "-rc:v", "vbr", "-cq:v", str(cq + 5)])
            else:
                cmd.extend(["-preset", "slow", "-rc:v", "vbr", "-cq:v", str(cq), "-b:v", vbr_target, "-maxrate:v", maxrate, "-bufsize", bufsize])
        else:
            if render_mode == "PROXY":
                cmd.extend(["-preset", "ultrafast", "-crf", str(cq + 5)])
            else:
                cmd.extend(["-preset", "slow", "-crf", str(cq)])
        
        # Add audio encoding
        if audio_path:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        
        # Add subtitle burning if present
        if subtitle_path and os.path.exists(subtitle_path):
            cmd.extend(["-vf", f"subtitles={subtitle_path}"])
        
        cmd.extend(["-r", str(self.fps), "-pix_fmt", "yuv420p", str(output_path)])
        
        # Execute
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Concatenation completed in {time.time() - start_time:.2f}s")
        except subprocess.CalledProcessError as e:
            logger.error(f"Concatenation failed: {e.stderr.decode()}")
            raise
        
        render_time = time.time() - start_time
        return render_time

    def render(
        self, 
        job_id: str, 
        image_paths: List[Path], 
        durations: List[float], 
        audio_path: Optional[Path] = None, 
        watermark: Optional[Path] = None, 
        overlay: Optional[Path] = None, 
        output_name: Optional[str] = None,
        subtitle_path: Optional[Path] = None,
        narrations: Optional[List[str]] = None,
        fast_path: Optional[bool] = None,
        encoder: Optional[str] = None,
        target_res: Optional[str] = None,
        render_mode: Optional[str] = None,
        cq: Optional[int] = None,
        vbr_target: Optional[str] = None,
        maxrate: Optional[str] = None,
        bufsize: Optional[str] = None,
        music_db: Optional[int] = None,
        watermark_pos: Optional[str] = None,
        upscale: Optional[str] = None,
        tmp_workdir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Render video from images and audio with GPU acceleration.
        
        Args:
            job_id: Job identifier
            image_paths: List of paths to image files
            durations: List of durations in seconds for each image
            audio_path: Optional path to audio file
            watermark: Optional watermark path
            overlay: Optional overlay image path (legacy, use watermark)
            output_name: Output filename
            subtitle_path: Optional SRT subtitle file path
            narrations: Optional list of narration texts for scene hashing
            fast_path: Enable GPU-accelerated FFmpeg rendering (default: from env FAST_PATH)
            encoder: Video encoder (h264_nvenc, hevc_nvenc, libx264) (default: from env ENCODER)
            target_res: Target resolution (720p, 1080p, 4k) (default: from env TARGET_RES)
            render_mode: PROXY (fast preview) or FINAL (production quality) (default: from env RENDER_MODE)
            cq: Constant quality value (lower = better, 18 recommended) (default: from env CQ)
            vbr_target: Variable bitrate target (e.g., "20M") (default: from env VBR_TARGET)
            maxrate: Maximum bitrate (e.g., "40M") (default: from env MAXRATE)
            bufsize: Buffer size (e.g., "80M") (default: from env BUFSIZE)
            music_db: Music volume in dB (negative = quieter) (default: from env MUSIC_DB)
            watermark_pos: Watermark position (tl, tr, bl, br) (default: from env WATERMARK_POS)
            upscale: Upscaling method (none, realesrgan, zscale) (default: from env UPSCALE)
            tmp_workdir: Temp directory for intermediates (default: from env TMP_WORKDIR)
            
        Returns:
            Dict with output_path, encoder, resolution, fast_path, timings
        """
        # Load defaults from environment
        if fast_path is None:
            fast_path = os.environ.get("FAST_PATH", "1") == "1"
        if encoder is None:
            encoder = os.environ.get("ENCODER", "h264_nvenc" if self.nvenc_available else "libx264")
        if target_res is None:
            target_res = os.environ.get("TARGET_RES", "1080p")
        if render_mode is None:
            render_mode = os.environ.get("RENDER_MODE", "FINAL")
        if cq is None:
            cq = int(os.environ.get("CQ", "18"))
        if vbr_target is None:
            vbr_target = os.environ.get("VBR_TARGET", "20M")
        if maxrate is None:
            maxrate = os.environ.get("MAXRATE", "40M")
        if bufsize is None:
            bufsize = os.environ.get("BUFSIZE", "80M")
        if music_db is None:
            music_db = int(os.environ.get("MUSIC_DB", "-12"))
        if watermark_pos is None:
            watermark_pos = os.environ.get("WATERMARK_POS", "br")
        if upscale is None:
            upscale = os.environ.get("UPSCALE", "none")
        if tmp_workdir is None:
            tmp_workdir = os.environ.get("TMP_WORKDIR", "/tmp/bhakti")
        
        out_name = output_name or f"{job_id}.mp4"
        output_path = self.output_dir / out_name
        
        # Fallback to libx264 if NVENC requested but not available
        if "nvenc" in encoder and not self.nvenc_available:
            logger.warning(f"{encoder} not available, falling back to libx264")
            encoder = "libx264"
        
        # Use fast path if enabled and FFmpeg available
        if fast_path:
            try:
                # Setup temp directory
                tmp_dir = Path(tmp_workdir) / job_id
                tmp_dir.mkdir(parents=True, exist_ok=True)
                
                # Render scenes in parallel
                scene_outputs = []
                total_scene_time = 0
                
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = []
                    for idx, (img_path, duration) in enumerate(zip(image_paths, durations)):
                        narration = narrations[idx] if narrations and idx < len(narrations) else ""
                        scene_hash = self._get_scene_hash(str(img_path), narration, duration)
                        
                        future = executor.submit(
                            self._render_scene_fastpath,
                            idx, str(img_path), duration, scene_hash, tmp_dir,
                            encoder, target_res, render_mode, cq, vbr_target, maxrate, bufsize
                        )
                        futures.append(future)
                    
                    for future in as_completed(futures):
                        scene_path, render_time = future.result()
                        scene_outputs.append(scene_path)
                        total_scene_time += render_time
                
                # Sort by scene index to maintain order
                scene_outputs.sort()
                
                # Concatenate with audio and effects
                concat_time = self._concat_scenes_fastpath(
                    scene_outputs, str(audio_path) if audio_path else None, 
                    str(watermark or overlay) if (watermark or overlay) else None, 
                    str(subtitle_path) if subtitle_path else None,
                    output_path, encoder, render_mode, cq, vbr_target, maxrate, bufsize,
                    music_db, watermark_pos, tmp_dir
                )
                
                # Cleanup temp files unless DEBUG mode
                if not os.environ.get("DEBUG"):
                    for scene_path in scene_outputs:
                        try:
                            os.remove(scene_path)
                        except Exception:
                            pass
                    try:
                        (tmp_dir / "concat.txt").unlink(missing_ok=True)
                    except Exception:
                        pass
                
                logger.info(f"Fast path render completed: {encoder} @ {target_res} in {total_scene_time + concat_time:.2f}s")
                
                return {
                    "output_path": str(output_path),
                    "encoder": encoder,
                    "resolution": target_res,
                    "fast_path": True,
                    "render_mode": render_mode,
                    "timings": {
                        "scene_rendering_sec": round(total_scene_time, 2),
                        "concat_sec": round(concat_time, 2),
                        "total_sec": round(total_scene_time + concat_time, 2)
                    }
                }
                
            except Exception as e:
                logger.error(f"Fast path failed: {e}, falling back to MoviePy")
                # Fall through to MoviePy fallback
        
        # MoviePy fallback
        logger.info("Using MoviePy fallback renderer")
        clips = []
        for img_path, dur in zip(image_paths, durations):
            clip = ImageClip(str(img_path)).set_duration(dur)
            clips.append(clip)
        if not clips:
            raise ValueError("No image clips provided")
        try:
            final = concatenate_videoclips(clips, method="compose")
        except Exception:
            final = concatenate_videoclips(clips)
        if audio_path and Path(audio_path).exists():
            audio = AudioFileClip(str(audio_path))
            final = final.set_audio(audio)
        if (watermark or overlay) and Path(watermark or overlay).exists():
            wm = ImageClip(str(watermark or overlay)).set_duration(final.duration)
            wm = wm.resize(width=400)
            wm = wm.set_pos(("right", "bottom"))
            final = CompositeVideoClip([final, wm])
        final.write_videofile(str(output_path), codec="libx264", fps=self.fps, threads=4, preset="medium")
        
        return {
            "output_path": str(output_path),
            "encoder": "libx264",
            "resolution": "default",
            "fast_path": False,
            "render_mode": "moviepy",
            "timings": None
        }


def run_selftest_real() -> Dict[str, Any]:
    """
    Self-test function for real video renderer with ffmpeg
    Tests actual rendering pipeline with minimal scene
    Returns comprehensive test results
    """
    import uuid
    import time
    
    print("\n" + "="*70)
    print("REAL RENDERER SELF-TEST")
    print("="*70 + "\n")
    
    results = {
        "passed": False,
        "tests": [],
        "errors": [],
        "job_id": None,
        "duration_sec": 0.0,
        "encoder_used": None,
        "fallback_reason": None
    }
    
    start_time = time.time()
    
    try:
        # Test 1: Check ffmpeg availability
        print("✓ Checking ffmpeg availability...")
        import shutil
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            results["errors"].append("FFmpeg not found in PATH")
            results["fallback_reason"] = "ffmpeg_not_found"
            return results
        
        print(f"  Found: {ffmpeg_path}")
        results["tests"].append({"name": "ffmpeg_available", "passed": True})
        
        # Test 2: Create test renderer
        print("✓ Creating video renderer...")
        job_id = str(uuid.uuid4())
        test_dir = Path("platform/pipeline_outputs") / job_id
        renderer = VideoRenderer(output_dir=test_dir, fps=24)
        results["job_id"] = job_id
        results["tests"].append({"name": "renderer_init", "passed": True})
        
        # Test 3: Check encoder support
        print("✓ Checking encoder support...")
        if renderer.nvenc_available:
            print("  ✅ NVENC (GPU acceleration) available")
            results["encoder_used"] = "h264_nvenc"
        else:
            print("  ⚠️  NVENC not available, will use libx264 (CPU)")
            results["encoder_used"] = "libx264"
        results["tests"].append({"name": "encoder_check", "passed": True})
        
        # Test 4: Create minimal test assets
        print("✓ Creating test assets...")
        from orchestrator import tiny_png, tiny_wav
        
        test_assets_dir = test_dir / "test_assets"
        test_assets_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test image
        test_image = test_assets_dir / "test.png"
        test_image.write_bytes(tiny_png())
        
        # Create test audio
        test_audio = test_assets_dir / "test.wav"
        test_audio.write_bytes(tiny_wav(duration_sec=1.0))
        
        results["tests"].append({"name": "test_assets", "passed": True})
        
        # Test 5: Attempt rendering
        print("✓ Attempting test render...")
        render_result = renderer.render(
            image_paths=[str(test_image)],
            durations=[1.0],
            audio_path=str(test_audio),
            output_filename="test_render.mp4",
            target_res="720p",
            fast_path=True
        )
        
        output_path = Path(render_result["output_path"])
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"✓ Render successful: {output_path}")
            print(f"  Encoder: {render_result.get('encoder')}")
            print(f"  Size: {output_path.stat().st_size} bytes")
            results["tests"].append({"name": "render_execution", "passed": True})
            results["encoder_used"] = render_result.get("encoder")
        else:
            results["errors"].append("Rendered file not created or empty")
        
        # All tests passed
        results["passed"] = len(results["errors"]) == 0
        results["duration_sec"] = time.time() - start_time
        
        if results["passed"]:
            print(f"\n{'='*70}")
            print(f"✅ REAL RENDERER SELFTEST PASSED ({results['duration_sec']:.2f}s)")
            print(f"{'='*70}\n")
        else:
            print(f"\n{'='*70}")
            print(f"❌ REAL RENDERER SELFTEST FAILED")
            for error in results["errors"]:
                print(f"   - {error}")
            print(f"{'='*70}\n")
        
    except Exception as e:
        results["passed"] = False
        results["errors"].append(f"Exception: {str(e)}")
        results["duration_sec"] = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"❌ REAL RENDERER SELFTEST FAILED")
        print(f"Exception: {e}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
    
    return results
