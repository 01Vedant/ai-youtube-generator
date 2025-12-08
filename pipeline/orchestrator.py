from pathlib import Path
import uuid
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

from .types import Scene, Asset, RenderJob
from .image_engine import ImageEngine
from .tts_engine import TTSEngine
from .subtitles import generate_srt, burn_in_subtitles
from .video_renderer import VideoRenderer
from .storage import Storage

logger = logging.getLogger(__name__)


def _retry(func, tries=2, delay=1, *args, **kwargs):
    last = None
    for _ in range(tries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last = e
            time.sleep(delay)
    raise last


class Orchestrator:
    def __init__(self, base_dir: Path = Path("platform/pipeline_outputs"), s3_config: Dict[str, Any] = None):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.s3_config = s3_config or {}

    def run(self, plan: Dict[str, Any], status_callback=None) -> Dict[str, Any]:
        job_id = plan.get("job_id") or uuid.uuid4().hex
        out_dir = self.base_dir / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        start = time.time()
        job = RenderJob(id=job_id, plan=plan, output_dir=out_dir)
        
        # Import guardrails for runtime limit
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "platform" / "backend"))
            from app.guardrails import Guardrails
            from app.metrics import job_timeouts_total
            runtime_limit_min = Guardrails.TOTAL_RUNTIME_LIMIT_MIN
        except Exception:
            runtime_limit_min = int(os.environ.get("TOTAL_RUNTIME_LIMIT_MIN", "30"))
            job_timeouts_total = None
        
        def check_timeout():
            """Check if runtime limit exceeded."""
            elapsed_min = (time.time() - start) / 60
            if elapsed_min > runtime_limit_min:
                if job_timeouts_total:
                    job_timeouts_total.inc()
                timeout_msg = (
                    f"Render exceeded time limit of {runtime_limit_min} minutes. "
                    f"This usually indicates a problem with the rendering pipeline. "
                    f"Please try again with fewer scenes or shorter durations."
                )
                raise TimeoutError(timeout_msg)
        
        def emit(step: str, progress: float, assets: Dict = None, log: str = None):
            """Emit status update via callback."""
            check_timeout()  # Check on every status update
            if status_callback:
                status_callback(step=step, progress=progress, assets=assets, log=log)
            if log:
                logger.info("[%s] %s (%.1f%%)", job_id, log, progress)
        
        try:
            emit("images", 5.0, log="Parsing plan and initializing engines...")
            scenes_input = plan.get("scenes", [])
            scenes: List[Scene] = []
            for idx, s in enumerate(scenes_input):
                sc = Scene(id=s.get("id") or f"scene-{idx}", prompt=s.get("prompt",""), narration=s.get("narration",""), duration=float(s.get("duration",3.0)))
                scenes.append(sc)
            image_engine = ImageEngine(out_dir / "images")
            tts_engine = TTSEngine(out_dir / "audio")
            renderer = VideoRenderer(out_dir / "renders")
            storage = Storage(**self.s3_config)
            
            # generate images in parallel
            emit("images", 10.0, log="Starting image generation...")
            img_futures = {}
            with ThreadPoolExecutor(max_workers=4) as ex:
                for sc in scenes:
                    img_futures[ex.submit(_retry, image_engine.generate, 2, 1, sc.id, sc.prompt, int(plan.get("images_per_scene",1)))] = sc
                completed = 0
                for fut in as_completed(img_futures):
                    sc = img_futures[fut]
                    try:
                        paths = fut.result()
                        sc.images = [Asset(id=uuid.uuid4().hex, path=p, type="image") for p in paths]
                        job.assets.extend(sc.images)
                        completed += 1
                        progress = 10.0 + (completed / len(scenes)) * 15.0
                        emit("images", progress, assets={"images_count": completed}, log=f"Generated images for scene {sc.id}")
                    except Exception as e:
                        logger.exception("Image generation failed for scene %s: %s", sc.id, e)
                        job.logs.append(f"image_failed:{sc.id}:{e}")
            
            # generate TTS in parallel
            emit("tts", 30.0, log="Starting TTS generation...")
            tts_futures = {}
            with ThreadPoolExecutor(max_workers=2) as ex:
                for sc in scenes:
                    tts_futures[ex.submit(_retry, tts_engine.generate, 2, 1, sc.id, sc.narration, plan.get("voice"))] = sc
                completed = 0
                for fut in as_completed(tts_futures):
                    sc = tts_futures[fut]
                    try:
                        path = fut.result()
                        sc.tts = Asset(id=uuid.uuid4().hex, path=path, type="audio")
                        job.assets.append(sc.tts)
                        completed += 1
                        progress = 30.0 + (completed / len(scenes)) * 15.0
                        emit("tts", progress, assets={"tts_count": completed}, log=f"Generated TTS for scene {sc.id}")
                    except Exception as e:
                        logger.exception("TTS generation failed for scene %s: %s", sc.id, e)
                        job.logs.append(f"tts_failed:{sc.id}:{e}")
            
            # subtitles
            emit("subtitles", 50.0, log="Generating subtitles...")
            srt_path = out_dir / "subtitles.en.srt"
            scenes_for_srt = [{"duration": sc.duration, "narration": sc.narration} for sc in scenes]
            generate_srt(scenes_for_srt, srt_path)
            job.assets.append(Asset(id=uuid.uuid4().hex, path=srt_path, type="srt"))
            emit("subtitles", 60.0, assets={"srt_path": str(srt_path)}, log="Subtitles generated")
            
            # render video
            emit("stitch", 65.0, log="Stitching video from images and audio...")
            image_paths = []
            durations = []
            narrations = []
            for sc in scenes:
                if sc.images:
                    image_paths.append(sc.images[0].path)
                    durations.append(sc.duration)
                    narrations.append(sc.narration)
            audio_concat = None
            if any(sc.tts for sc in scenes):
                # naive single audio: concat scene audios sequentially
                concat_path = out_dir / "narration_concat.wav"
                from pydub import AudioSegment
                combined = None
                for sc in scenes:
                    if sc.tts and sc.tts.path.exists():
                        seg = AudioSegment.from_file(str(sc.tts.path))
                        combined = seg if combined is None else combined + seg
                if combined is not None:
                    combined.export(str(concat_path), format="wav")
                    audio_concat = concat_path
                    job.assets.append(Asset(id=uuid.uuid4().hex, path=concat_path, type="audio"))
            
            # Pass fast-path options to renderer (from plan or env)
            render_result = renderer.render(
                job_id, 
                image_paths, 
                durations, 
                audio_path=audio_concat, 
                watermark=plan.get("watermark_path"),
                subtitle_path=srt_path if plan.get("soft_subtitles") else None,
                narrations=narrations,
                fast_path=plan.get("fast_path"),
                encoder=plan.get("encoder"),
                target_res=plan.get("target_res"),
                render_mode=plan.get("render_mode"),
                cq=plan.get("cq"),
                vbr_target=plan.get("vbr_target"),
                maxrate=plan.get("maxrate"),
                bufsize=plan.get("bufsize"),
                music_db=plan.get("music_db"),
                watermark_pos=plan.get("watermark_pos"),
                upscale=plan.get("upscale"),
                tmp_workdir=plan.get("tmp_workdir")
            )
            final_video = Path(render_result["output_path"])
            job.assets.append(Asset(id=uuid.uuid4().hex, path=final_video, type="video"))
            emit("stitch", 85.0, assets={"video_path": str(final_video)}, log=f"Video stitching complete using {render_result.get('encoder', 'unknown')} @ {render_result.get('resolution', 'default')}")
            
            # optional burn-in
            if plan.get("burn_in_subtitles"):
                emit("stitch", 87.0, log="Burning subtitles into video...")
                burned = out_dir / f"{job_id}.burned.mp4"
                burn_in_subtitles(final_video, srt_path, burned)
                job.assets.append(Asset(id=uuid.uuid4().hex, path=burned, type="video_burned"))
                final_video = burned
            
            # upload outputs
            emit("upload", 90.0, log="Uploading assets to storage...")
            upload_results = []
            for a in job.assets:
                try:
                    res = storage.upload_file(a.path, remote_path=f"{job_id}/{a.path.name}")
                    upload_results.append({"asset": str(a.path.name), "upload": res})
                except Exception as e:
                    logger.exception("Upload failed for %s: %s", a.path, e)
            emit("upload", 95.0, log="Upload complete")
            
            # Optional YouTube upload
            youtube_url = None
            if plan.get("enable_youtube_upload"):
                import os
                if os.environ.get("ENABLE_YOUTUBE_UPLOAD") == "1":
                    emit("youtube_publish", 96.0, log="Uploading to YouTube...")
                    try:
                        import sys
                        sys.path.insert(0, str(Path(__file__).parent.parent))
                        from services.youtube_service import YouTubeService
                        yt_service = YouTubeService()
                        if yt_service.is_enabled():
                            title = YouTubeService.generate_title(plan)
                            description = YouTubeService.generate_description(plan, job_id)
                            yt_result = yt_service.upload_video(
                                final_video,
                                title=title,
                                description=description,
                                tags=["sanatan-dharma", "devotional", "ai-generated"],
                                privacy_status="public"
                            )
                            if yt_result.get("success"):
                                youtube_url = yt_result.get("url")
                                emit("youtube_publish", 99.0, assets={"youtube_url": youtube_url}, log=f"Video published: {youtube_url}")
                            else:
                                logger.warning("YouTube upload failed: %s", yt_result.get("error"))
                    except Exception as e:
                        logger.warning("YouTube upload step failed: %s", e)
            
            job.end_time = time.time()
            job.status = "finished"
            job.durations = {"total": job.end_time - job.start_time}
            summary = {
                "job_id": job.id,
                "status": job.status,
                "start_time": job.start_time,
                "end_time": job.end_time,
                "durations": job.durations,
                "assets": [{"path": str(a.path), "type": a.type} for a in job.assets],
                "uploads": upload_results,
                "youtube_url": youtube_url,
                "logs": job.logs,
                "encoder": render_result.get("encoder"),
                "resolution": render_result.get("resolution"),
                "fast_path": render_result.get("fast_path", False),
                "render_mode": render_result.get("render_mode"),
                "render_timings": render_result.get("timings"),
            }
            summary_path = out_dir / "job_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2))
            emit("upload", 100.0, log=f"Job {job_id} completed successfully")
            return summary
        except TimeoutError as e:
            # Handle timeout specially - still cleanup
            job.end_time = time.time()
            job.status = "failed"
            job.logs.append(f"TIMEOUT: {str(e)}")
            summary = {"job_id": job.id, "status": "timeout", "error": str(e), "logs": job.logs}
            (out_dir / "job_summary.json").write_text(json.dumps(summary, indent=2))
            logger.error("Job timeout: %s", e)
            
            # Cleanup temp files even on timeout
            try:
                import shutil
                tmp_dir = Path(os.environ.get("TMP_WORKDIR", "/tmp/bhakti")) / job_id
                if tmp_dir.exists() and not os.environ.get("DEBUG"):
                    shutil.rmtree(tmp_dir)
            except Exception as cleanup_err:
                logger.warning("Cleanup failed after timeout: %s", cleanup_err)
            
            return summary
        except Exception as e:
            job.end_time = time.time()
            job.status = "failed"
            job.logs.append(str(e))
            summary = {"job_id": job.id, "status": job.status, "logs": job.logs}
            (out_dir / "job_summary.json").write_text(json.dumps(summary, indent=2))
            emit("error", 0.0, log=f"Job failed: {e}")
            logger.exception("Orchestration failed: %s", e)
            return summary
