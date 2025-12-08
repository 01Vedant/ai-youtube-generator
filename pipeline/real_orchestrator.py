"""
Real Orchestrator: Production rendering with FFmpeg, graceful MoviePy fallback
Matches simulator step names: images → tts → subtitles → stitch → upload → completed
"""
from pathlib import Path
import uuid
import json
import logging
import time
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class RealOrchestrator:
    """Production orchestrator with FFmpeg detection and automatic fallback"""
    
    def __init__(self, base_dir: Path = Path("platform/pipeline_outputs")):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.status_callback = None
        
        # Detect capabilities
        self.ffmpeg_available = self._check_ffmpeg()
        self.nvenc_available = self._check_nvenc() if self.ffmpeg_available else False
        
        # Select encoder
        if self.nvenc_available:
            self.encoder = "h264_nvenc"
            self.fast_path = True
        elif self.ffmpeg_available:
            self.encoder = "libx264"
            self.fast_path = False
        else:
            self.encoder = "moviepy"
            self.fast_path = False
        
        logger.info(f"RealOrchestrator initialized: encoder={self.encoder}, fast_path={self.fast_path}")
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        return bool(shutil.which("ffmpeg"))
    
    def _check_nvenc(self) -> bool:
        """Check if NVENC encoder is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "h264_nvenc" in result.stdout
        except Exception:
            return False
    
    def _emit_status(self, step: str, progress_pct: int, meta: Optional[Dict] = None):
        """Emit status update via callback"""
        if self.status_callback:
            self.status_callback(step, progress_pct, meta)
    
    def run(self, plan: Dict[str, Any], status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Run real rendering pipeline with FFmpeg/MoviePy fallback.
        
        Steps match simulator: images → tts → subtitles → stitch → upload → completed
        
        Returns:
            dict with job_id, state, assets, final_video_url, encoder, timings, etc.
        """
        # Use provided callback or fall back to instance callback
        original_callback = self.status_callback
        if status_callback:
            self.status_callback = status_callback
        
        start_time = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        
        # Generate job_id
        job_id = str(uuid.uuid4())
        
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
        step_timings = {}
        
        def log(msg: str):
            elapsed_ms = int((time.time() - start_time) * 1000)
            logs.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": "info",
                "message": f"[{elapsed_ms}ms] {msg}"
            })
            print(f"[REAL {job_id[:8]}] [{elapsed_ms}ms] {msg}")
        
        try:
            # Step 1: Images (using placeholder/generator)
            step_start = time.time()
            log("Generating images...")
            self._emit_status("images", 10, {"job_id": job_id})
            
            num_scenes = len(plan.get("scenes", [{"id": 1}]))
            # In production, this would call image generation API
            # For now, create placeholder images
            from PIL import Image
            for i in range(num_scenes):
                scene_num = i + 1
                img_path = images_dir / f"scene_{scene_num:03d}.png"
                
                # Create simple gradient image
                img = Image.new("RGB", (1920, 1080), color=(20 + i*20, 40 + i*15, 60 + i*10))
                img.save(img_path)
                
                assets.append({
                    "type": "image",
                    "label": f"Scene {scene_num}",
                    "path": f"images/scene_{scene_num:03d}.png"
                })
            
            step_timings["images_ms"] = int((time.time() - step_start) * 1000)
            self._emit_status("images", 30, {"completed": num_scenes})
            log(f"Generated {num_scenes} images")
            
            # Step 2: TTS (text-to-speech)
            step_start = time.time()
            log("Generating audio...")
            self._emit_status("tts", 40, {})
            
            # In production, this would call TTS API
            # For now, create silent audio files
            for i in range(num_scenes):
                scene_num = i + 1
                audio_path = audio_dir / f"scene_{scene_num:03d}.wav"
                
                # Create 3-second silent WAV
                self._create_silent_wav(audio_path, duration_sec=3.0)
                
                assets.append({
                    "type": "audio",
                    "label": f"Scene {scene_num} Audio",
                    "path": f"audio/scene_{scene_num:03d}.wav"
                })
            
            step_timings["audio_ms"] = int((time.time() - step_start) * 1000)
            self._emit_status("tts", 55, {"completed": num_scenes})
            log(f"Generated {num_scenes} audio clips")
            
            # Step 3: Subtitles
            step_start = time.time()
            log("Generating subtitles...")
            self._emit_status("subtitles", 65, {})
            
            for lang in ["en", "hi"]:
                srt_path = subs_dir / f"subs_{lang}.srt"
                srt_content = self._generate_simple_srt(num_scenes, lang)
                srt_path.write_text(srt_content, encoding="utf-8")
                
                assets.append({
                    "type": "srt",
                    "label": f"Subtitles ({lang.upper()})",
                    "path": f"subs/subs_{lang}.srt"
                })
            
            step_timings["subtitles_ms"] = int((time.time() - step_start) * 1000)
            self._emit_status("subtitles", 75, {})
            log("Generated subtitles")
            
            # Step 4: Stitch (create final video)
            step_start = time.time()
            log(f"Stitching video using {self.encoder}...")
            self._emit_status("stitch", 80, {"encoder": self.encoder})
            
            final_video = final_dir / "final.mp4"
            
            if self.ffmpeg_available:
                self._stitch_with_ffmpeg(images_dir, audio_dir, final_video, num_scenes)
            else:
                self._stitch_with_moviepy(images_dir, audio_dir, final_video, num_scenes)
            
            step_timings["stitch_ms"] = int((time.time() - step_start) * 1000)
            self._emit_status("stitch", 90, {})
            log("Video stitching complete")
            
            # Step 5: Upload (simulated for now)
            step_start = time.time()
            log("Finalizing...")
            self._emit_status("upload", 95, {})
            
            # In production, would upload to CDN/S3
            time.sleep(0.1)
            
            step_timings["upload_ms"] = int((time.time() - step_start) * 1000)
            log("Finalization complete")
            
            # Step 6: Completed
            finished_at = datetime.now(timezone.utc).isoformat()
            elapsed_sec = time.time() - start_time
            elapsed_ms = int(elapsed_sec * 1000)
            
            self._emit_status("completed", 100, {"elapsed_sec": elapsed_sec})
            log(f"Job completed in {elapsed_sec:.2f}s")
            
            # Write job summary
            step_timings["total_ms"] = elapsed_ms
            
            summary = {
                "job_id": job_id,
                "state": "success",
                "step": "completed",
                "progress": 100,
                "started_at": started_at,
                "finished_at": finished_at,
                "elapsed_sec": elapsed_sec,
                "encoder": self.encoder,
                "resolution": plan.get("resolution", "1080p"),
                "fast_path": self.fast_path,
                "proxy": plan.get("proxy", False),
                "assets": assets,
                "final_video_url": f"/artifacts/{job_id}/final/final.mp4",
                "timings": step_timings,
                "fallback_reason": None if self.ffmpeg_available else "FFmpeg not available, using MoviePy",
                "logs": logs,
                "error": None,
                "plan": plan  # Store original plan for retry/duplicate
            }
            
            summary_path = job_dir / "job_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            
            return summary
            
        except Exception as e:
            error_msg = str(e)
            log(f"ERROR: {error_msg}")
            self._emit_status("error", 0, {"error": error_msg})
            
            finished_at = datetime.now(timezone.utc).isoformat()
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            summary = {
                "job_id": job_id,
                "state": "error",
                "step": "error",
                "progress": 0,
                "started_at": started_at,
                "finished_at": finished_at,
                "encoder": self.encoder,
                "error": error_msg,
                "timings": {"total_ms": elapsed_ms, **step_timings},
                "logs": logs,
                "plan": plan  # Store original plan for retry/duplicate
            }
            
            summary_path = job_dir / "job_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            
            # Restore original callback
            if status_callback:
                self.status_callback = original_callback
            
            return summary
        
        # Restore original callback (success path)
        if status_callback:
            self.status_callback = original_callback
    
    def _create_silent_wav(self, output_path: Path, duration_sec: float = 3.0):
        """Create silent WAV file"""
        try:
            # Try pydub first
            from pydub import AudioSegment
            silence = AudioSegment.silent(duration=int(duration_sec * 1000))
            silence.export(output_path, format="wav")
        except ImportError:
            # Fallback: write minimal WAV header
            sample_rate = 44100
            num_samples = int(sample_rate * duration_sec)
            data = b'\x00' * (num_samples * 2)  # 16-bit mono
            
            with open(output_path, 'wb') as f:
                # WAV header
                f.write(b'RIFF')
                f.write((36 + len(data)).to_bytes(4, 'little'))
                f.write(b'WAVE')
                f.write(b'fmt ')
                f.write((16).to_bytes(4, 'little'))
                f.write((1).to_bytes(2, 'little'))  # PCM
                f.write((1).to_bytes(2, 'little'))  # mono
                f.write(sample_rate.to_bytes(4, 'little'))
                f.write((sample_rate * 2).to_bytes(4, 'little'))  # byte rate
                f.write((2).to_bytes(2, 'little'))  # block align
                f.write((16).to_bytes(2, 'little'))  # bits per sample
                f.write(b'data')
                f.write(len(data).to_bytes(4, 'little'))
                f.write(data)
    
    def _generate_simple_srt(self, num_scenes: int, lang: str) -> str:
        """Generate simple SRT subtitle file"""
        lines = []
        for i in range(num_scenes):
            start_sec = i * 3
            end_sec = (i + 1) * 3
            lines.append(f"{i + 1}")
            lines.append(f"{self._format_srt_time(start_sec)} --> {self._format_srt_time(end_sec)}")
            lines.append(f"Scene {i + 1} narration ({lang})")
            lines.append("")
        return "\n".join(lines)
    
    def _format_srt_time(self, seconds: int) -> str:
        """Format seconds as SRT timestamp"""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d},000"
    
    def _stitch_with_ffmpeg(self, images_dir: Path, audio_dir: Path, output_path: Path, num_scenes: int):
        """Stitch video using FFmpeg"""
        # Create concat file for images
        concat_file = images_dir.parent / "concat.txt"
        with open(concat_file, 'w') as f:
            for i in range(num_scenes):
                img_path = images_dir / f"scene_{i+1:03d}.png"
                f.write(f"file '{img_path}'\n")
                f.write("duration 3\n")
        
        # Simple FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", self.encoder,
            "-pix_fmt", "yuv420p",
            "-r", "24",
            str(output_path)
        ]
        
        # Add encoder-specific options
        if self.encoder == "h264_nvenc":
            cmd.extend(["-preset", "fast", "-rc", "vbr", "-cq", "23"])
        elif self.encoder == "libx264":
            cmd.extend(["-preset", "medium", "-crf", "23"])
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def _stitch_with_moviepy(self, images_dir: Path, audio_dir: Path, output_path: Path, num_scenes: int):
        """Stitch video using MoviePy (fallback)"""
        from moviepy.editor import ImageClip, concatenate_videoclips
        
        clips = []
        for i in range(num_scenes):
            img_path = images_dir / f"scene_{i+1:03d}.png"
            clip = ImageClip(str(img_path), duration=3)
            clips.append(clip)
        
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )


# Self-test function
def run_selftest_real() -> Dict[str, Any]:
    """
    Self-test for real orchestrator.
    Tests FFmpeg detection, encoder availability, and full render pipeline.
    """
    from datetime import datetime
    
    results = {
        "passed": False,
        "tests": [],
        "errors": [],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print("\n" + "="*70)
    print("REAL ORCHESTRATOR SELF-TEST")
    print("="*70 + "\n")
    
    try:
        # Test 1: FFmpeg detection
        print("✓ Checking FFmpeg availability...")
        orch = RealOrchestrator(base_dir=Path("platform/pipeline_outputs"))
        
        if not orch.ffmpeg_available:
            print("⚠ FFmpeg not found - will use MoviePy fallback")
            results["tests"].append({"name": "ffmpeg_check", "passed": False, "fallback": True})
        else:
            print(f"✓ FFmpeg available with encoder: {orch.encoder}")
            results["tests"].append({"name": "ffmpeg_check", "passed": True})
        
        # Test 2: Create test plan
        print("✓ Creating test plan (1 scene)...")
        plan = {
            "topic": "Real render test",
            "scenes": [{"image_prompt": "test", "narration": "test", "duration_sec": 3}],
            "fast_path": orch.fast_path,
            "proxy": True
        }
        
        # Test 3: Run orchestrator
        status_updates = []
        def test_callback(step: str, progress: int, meta: dict = None):
            status_updates.append({"step": step, "progress": progress})
        
        print("✓ Running real render...")
        summary = orch.run(plan, status_callback=test_callback)
        
        # Test 4: Validate status progression
        print(f"✓ Received {len(status_updates)} status updates")
        if len(status_updates) >= 5:
            results["tests"].append({"name": "status_updates", "passed": True})
        else:
            results["errors"].append(f"Expected >=5 status updates, got {len(status_updates)}")
        
        # Test 5: Validate job_summary.json
        job_dir = Path("platform/pipeline_outputs") / summary.get("job_id")
        summary_path = job_dir / "job_summary.json"
        
        if summary_path.exists():
            print(f"✓ job_summary.json created at {summary_path}")
            results["tests"].append({"name": "summary_file", "passed": True})
            
            # Validate structure
            summary_data = json.loads(summary_path.read_text())
            required_fields = ["job_id", "state", "encoder", "timings", "final_video_url"]
            missing = [f for f in required_fields if f not in summary_data]
            
            if not missing:
                results["tests"].append({"name": "summary_structure", "passed": True})
                print(f"✓ Encoder: {summary_data.get('encoder')}")
                print(f"✓ Fast path: {summary_data.get('fast_path')}")
                print(f"✓ Timings: {summary_data.get('timings')}")
            else:
                results["errors"].append(f"Missing fields: {missing}")
        else:
            results["errors"].append("job_summary.json not created")
        
        # Test 6: Validate final video exists
        final_video = job_dir / "final" / "final.mp4"
        if final_video.exists():
            print(f"✓ Final video created: {final_video.stat().st_size} bytes")
            results["tests"].append({"name": "video_file", "passed": True})
        else:
            results["errors"].append("Final video not created")
        
        # Determine overall pass/fail
        results["passed"] = len(results["errors"]) == 0
        
        duration = summary.get("elapsed_sec", 0)
        
        print("\n" + "="*70)
        if results["passed"]:
            print(f"✅ REAL ORCHESTRATOR SELFTEST PASSED ({duration:.2f}s)")
        else:
            print(f"❌ REAL ORCHESTRATOR SELFTEST FAILED")
            for err in results["errors"]:
                print(f"   - {err}")
        print("="*70 + "\n")
        
    except Exception as e:
        results["passed"] = False
        results["errors"].append(str(e))
        print(f"\n❌ SELFTEST EXCEPTION: {e}\n")
    
    return results
