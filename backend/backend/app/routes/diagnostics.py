"""
Diagnostics and preflight checks for production readiness.
Returns health status for GPU, providers, storage, and system resources.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class PreflightResponse(BaseModel):
    """Preflight check results."""
    ffmpeg_ok: bool
    nvenc_ok: bool
    disk_free_gb: float
    tmp_writable: bool
    s3_write_ok: Optional[bool] = None
    openai_ok: Optional[bool] = None
    elevenlabs_ok: Optional[bool] = None
    youtube_ok: Optional[bool] = None
    checks: Dict[str, Dict[str, Any]]


def check_ffmpeg() -> Dict[str, Any]:
    """Check if FFmpeg is available and working."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return {
            "ok": result.returncode == 0,
            "version": result.stdout.split("\n")[0] if result.returncode == 0 else None,
            "reason": None if result.returncode == 0 else "FFmpeg not responding"
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "version": None, "reason": "FFmpeg timeout"}
    except FileNotFoundError:
        return {"ok": False, "version": None, "reason": "FFmpeg not installed"}
    except Exception as e:
        return {"ok": False, "version": None, "reason": f"FFmpeg error: {str(e)}"}


def check_nvenc() -> Dict[str, Any]:
    """Check if NVENC hardware encoding is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            timeout=2
        )
        has_h264 = "h264_nvenc" in result.stdout
        has_hevc = "hevc_nvenc" in result.stdout
        
        if has_h264 or has_hevc:
            encoders = []
            if has_h264:
                encoders.append("h264_nvenc")
            if has_hevc:
                encoders.append("hevc_nvenc")
            return {
                "ok": True,
                "encoders": encoders,
                "reason": None
            }
        else:
            return {
                "ok": False,
                "encoders": [],
                "reason": "NVENC not available (CPU fallback will be used)"
            }
    except Exception as e:
        return {"ok": False, "encoders": [], "reason": f"NVENC check failed: {str(e)}"}


def check_disk_space() -> Dict[str, Any]:
    """Check available disk space in GB."""
    try:
        usage = shutil.disk_usage(os.getcwd())
        free_gb = usage.free / (1024 ** 3)
        return {
            "ok": free_gb > 2.0,
            "free_gb": round(free_gb, 2),
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "reason": "Low disk space" if free_gb <= 2.0 else None
        }
    except Exception as e:
        return {"ok": False, "free_gb": 0, "total_gb": 0, "reason": f"Disk check failed: {str(e)}"}


def check_tmp_writable() -> Dict[str, Any]:
    """Check if TMP_WORKDIR is writable."""
    try:
        tmp_dir = Path(os.environ.get("TMP_WORKDIR", "/tmp/bhakti"))
        tmp_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = tmp_dir / f"preflight_test_{time.time()}.txt"
        test_file.write_text("test")
        test_file.unlink()
        
        return {
            "ok": True,
            "path": str(tmp_dir),
            "reason": None
        }
    except Exception as e:
        return {"ok": False, "path": str(tmp_dir), "reason": f"TMP not writable: {str(e)}"}


def check_s3() -> Optional[Dict[str, Any]]:
    """Check S3 connectivity if configured."""
    if not os.environ.get("S3_BUCKET"):
        return None
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3 = boto3.client(
            's3',
            endpoint_url=os.environ.get("S3_ENDPOINT"),
            aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("S3_SECRET_KEY")
        )
        
        bucket = os.environ.get("S3_BUCKET")
        test_key = f"preflight_test_{time.time()}.txt"
        
        # Try to put and delete a test object
        s3.put_object(Bucket=bucket, Key=test_key, Body=b"test")
        s3.delete_object(Bucket=bucket, Key=test_key)
        
        return {
            "ok": True,
            "bucket": bucket,
            "reason": None
        }
    except ClientError as e:
        return {
            "ok": False,
            "bucket": os.environ.get("S3_BUCKET"),
            "reason": f"S3 error: {e.response['Error']['Code']}"
        }
    except Exception as e:
        return {"ok": False, "bucket": os.environ.get("S3_BUCKET"), "reason": f"S3 check failed: {str(e)}"}


def check_openai() -> Optional[Dict[str, Any]]:
    """Check OpenAI API if configured."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    
    try:
        import openai
        openai.api_key = api_key
        
        # Simple API call with timeout
        response = openai.models.list(timeout=2)
        
        return {
            "ok": True,
            "models_count": len(response.data) if hasattr(response, 'data') else 0,
            "reason": None
        }
    except openai.AuthenticationError:
        return {"ok": False, "reason": "OpenAI authentication failed - check API key"}
    except openai.RateLimitError:
        return {"ok": False, "reason": "OpenAI rate limit exceeded"}
    except Exception as e:
        return {"ok": False, "reason": f"OpenAI check failed: {str(e)}"}


def check_elevenlabs() -> Optional[Dict[str, Any]]:
    """Check ElevenLabs API if configured."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return None
    
    try:
        import requests
        
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key},
            timeout=2
        )
        
        if response.status_code == 200:
            voices = response.json().get("voices", [])
            return {
                "ok": True,
                "voices_count": len(voices),
                "reason": None
            }
        elif response.status_code == 401:
            return {"ok": False, "reason": "ElevenLabs authentication failed - check API key"}
        else:
            return {"ok": False, "reason": f"ElevenLabs API returned {response.status_code}"}
    except requests.Timeout:
        return {"ok": False, "reason": "ElevenLabs API timeout"}
    except Exception as e:
        return {"ok": False, "reason": f"ElevenLabs check failed: {str(e)}"}


def check_youtube() -> Optional[Dict[str, Any]]:
    """Check YouTube API if configured."""
    if os.environ.get("ENABLE_YOUTUBE_UPLOAD") != "1":
        return None
    
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        return {
            "ok": False,
            "reason": "YouTube OAuth credentials not configured"
        }
    
    # Check if we have valid tokens
    try:
        from pathlib import Path
        token_file = Path("platform/youtube_tokens.json")
        
        if not token_file.exists():
            return {
                "ok": False,
                "reason": "YouTube not authenticated - run OAuth flow first"
            }
        
        import json
        tokens = json.loads(token_file.read_text())
        
        if "access_token" not in tokens:
            return {
                "ok": False,
                "reason": "YouTube token file invalid"
            }
        
        return {
            "ok": True,
            "authenticated": True,
            "reason": None
        }
    except Exception as e:
        return {"ok": False, "reason": f"YouTube check failed: {str(e)}"}


@router.get("/preflight", response_model=PreflightResponse)
async def preflight_check() -> PreflightResponse:
    """
    Comprehensive preflight check for all system components.
    
    Returns:
        PreflightResponse with status of all components
    """
    checks = {}
    
    # Core requirements (always checked)
    ffmpeg_result = check_ffmpeg()
    checks["ffmpeg"] = ffmpeg_result
    
    nvenc_result = check_nvenc()
    checks["nvenc"] = nvenc_result
    
    disk_result = check_disk_space()
    checks["disk"] = disk_result
    
    tmp_result = check_tmp_writable()
    checks["tmp"] = tmp_result
    
    # Optional providers (only if configured)
    s3_result = check_s3()
    if s3_result:
        checks["s3"] = s3_result
    
    openai_result = check_openai()
    if openai_result:
        checks["openai"] = openai_result
    
    elevenlabs_result = check_elevenlabs()
    if elevenlabs_result:
        checks["elevenlabs"] = elevenlabs_result
    
    youtube_result = check_youtube()
    if youtube_result:
        checks["youtube"] = youtube_result
    
    return PreflightResponse(
        ffmpeg_ok=ffmpeg_result["ok"],
        nvenc_ok=nvenc_result["ok"],
        disk_free_gb=disk_result["free_gb"],
        tmp_writable=tmp_result["ok"],
        s3_write_ok=s3_result["ok"] if s3_result else None,
        openai_ok=openai_result["ok"] if openai_result else None,
        elevenlabs_ok=elevenlabs_result["ok"] if elevenlabs_result else None,
        youtube_ok=youtube_result["ok"] if youtube_result else None,
        checks=checks
    )
