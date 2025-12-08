"""
Environment Auto-Detection and Self-Configuration
Automatically detects ffmpeg, encoders, and sets SIMULATE_RENDER mode
"""
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class EnvironmentDetector:
    """Detects available rendering capabilities and auto-configures environment"""
    
    def __init__(self):
        self.ffmpeg_path: Optional[str] = None
        self.ffprobe_path: Optional[str] = None
        self.has_nvenc: bool = False
        self.has_h264: bool = False
        self.has_write_access: bool = False
        self.simulate_mode: bool = True
        self.detection_report: Dict[str, Any] = {}
    
    def detect_all(self) -> Dict[str, Any]:
        """Run all detection checks and return comprehensive report"""
        logger.info("Starting environment detection...")
        
        # 1. Check ffmpeg availability
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
        
        # 2. Check encoder support
        if self.ffmpeg_path:
            self.has_nvenc = self._check_encoder("h264_nvenc")
            self.has_h264 = self._check_encoder("libx264")
        
        # 3. Check write access to pipeline_outputs
        self.has_write_access = self._check_write_access()
        
        # 4. Determine simulate mode (unless explicitly set)
        self.simulate_mode = self._determine_simulate_mode()
        
        # 5. Build report
        self.detection_report = {
            "ffmpeg": {
                "available": self.ffmpeg_path is not None,
                "path": self.ffmpeg_path,
                "version": self._get_ffmpeg_version() if self.ffmpeg_path else None
            },
            "encoders": {
                "h264_nvenc": self.has_nvenc,
                "libx264": self.has_h264,
                "available": self.has_nvenc or self.has_h264
            },
            "filesystem": {
                "pipeline_outputs_writable": self.has_write_access,
                "platform_root": str(Path(__file__).resolve().parents[1])
            },
            "mode": {
                "simulate_render": self.simulate_mode,
                "reason": self._get_mode_reason(),
                "override": os.getenv("SIMULATE_RENDER") is not None
            }
        }
        
        logger.info(f"Environment detection complete. Simulate mode: {self.simulate_mode}")
        return self.detection_report
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find ffmpeg executable in PATH or common locations"""
        # Check PATH first
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        
        # Check common Windows locations
        if sys.platform == "win32":
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
                os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe")
            ]
            for path in common_paths:
                if Path(path).exists():
                    return path
        
        return None
    
    def _find_ffprobe(self) -> Optional[str]:
        """Find ffprobe executable"""
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            return ffprobe
        
        # If we found ffmpeg, ffprobe should be in same directory
        if self.ffmpeg_path:
            ffprobe_path = Path(self.ffmpeg_path).parent / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
            if ffprobe_path.exists():
                return str(ffprobe_path)
        
        return None
    
    def _check_encoder(self, encoder_name: str) -> bool:
        """Check if specific encoder is available in ffmpeg"""
        if not self.ffmpeg_path:
            return False
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-encoders"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return encoder_name in result.stdout
        except Exception as e:
            logger.warning(f"Failed to check encoder {encoder_name}: {e}")
            return False
    
    def _get_ffmpeg_version(self) -> Optional[str]:
        """Get ffmpeg version string"""
        if not self.ffmpeg_path:
            return None
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            # Extract first line (version info)
            first_line = result.stdout.split('\n')[0]
            return first_line.replace("ffmpeg version ", "").split()[0]
        except Exception as e:
            logger.warning(f"Failed to get ffmpeg version: {e}")
            return None
    
    def _check_write_access(self) -> bool:
        """Check if we can write to pipeline_outputs directory"""
        try:
            output_dir = Path("platform/pipeline_outputs")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Try writing a test file
            test_file = output_dir / ".env_test"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            logger.error(f"No write access to pipeline_outputs: {e}")
            return False
    
    def _determine_simulate_mode(self) -> bool:
        """Determine if we should use simulate mode"""
        # Check if explicitly set
        env_value = os.getenv("SIMULATE_RENDER")
        if env_value is not None:
            return int(env_value) == 1
        
        # Auto-detect: use real mode only if ffmpeg is available with encoders
        if self.ffmpeg_path and (self.has_nvenc or self.has_h264):
            logger.info("FFmpeg with encoders detected - using REAL mode (SIMULATE_RENDER=0)")
            os.environ["SIMULATE_RENDER"] = "0"
            return False
        else:
            logger.info("FFmpeg not available - using SIMULATOR mode (SIMULATE_RENDER=1)")
            os.environ["SIMULATE_RENDER"] = "1"
            return True
    
    def _get_mode_reason(self) -> str:
        """Get human-readable reason for mode selection"""
        env_value = os.getenv("SIMULATE_RENDER")
        if env_value is not None:
            return "Explicitly set via SIMULATE_RENDER environment variable"
        
        if not self.ffmpeg_path:
            return "FFmpeg not found in PATH or common locations"
        
        if not (self.has_nvenc or self.has_h264):
            return "FFmpeg found but no H.264 encoders available"
        
        return "FFmpeg with encoders detected - real rendering available"
    
    def print_report(self):
        """Print formatted detection report to console"""
        report = self.detection_report
        
        print("\n" + "="*70)
        print("BHAKTI VIDEO GENERATOR - ENVIRONMENT REPORT")
        print("="*70)
        
        # FFmpeg status
        print("\n📹 FFmpeg Detection:")
        if report["ffmpeg"]["available"]:
            print(f"  ✅ Found: {report['ffmpeg']['path']}")
            print(f"  📦 Version: {report['ffmpeg']['version']}")
        else:
            print("  ❌ Not found in PATH")
        
        # Encoder status
        print("\n🎬 Video Encoders:")
        if report["encoders"]["h264_nvenc"]:
            print("  ✅ h264_nvenc (NVIDIA GPU acceleration)")
        else:
            print("  ❌ h264_nvenc (not available)")
        
        if report["encoders"]["libx264"]:
            print("  ✅ libx264 (CPU encoding)")
        else:
            print("  ❌ libx264 (not available)")
        
        # Filesystem
        print("\n💾 Filesystem:")
        if report["filesystem"]["pipeline_outputs_writable"]:
            print("  ✅ pipeline_outputs/ writable")
        else:
            print("  ❌ pipeline_outputs/ not writable")
        
        print(f"  📁 Platform root: {report['filesystem']['platform_root']}")
        
        # Mode selection
        print("\n⚙️  Render Mode:")
        mode_str = "SIMULATOR (dev/testing)" if report["mode"]["simulate_render"] else "REAL (production)"
        print(f"  🎯 Selected: {mode_str}")
        print(f"  💡 Reason: {report['mode']['reason']}")
        if report["mode"]["override"]:
            print("  🔧 Override: Environment variable SIMULATE_RENDER set")
        
        print("\n" + "="*70)
        print()


# Global singleton instance
_detector: Optional[EnvironmentDetector] = None


def get_detector() -> EnvironmentDetector:
    """Get or create global environment detector"""
    global _detector
    if _detector is None:
        _detector = EnvironmentDetector()
        _detector.detect_all()
    return _detector


def auto_configure_environment() -> Dict[str, Any]:
    """Auto-configure environment and return report (call at startup)"""
    detector = get_detector()
    detector.print_report()
    return detector.detection_report
