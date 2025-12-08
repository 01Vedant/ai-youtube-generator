import os
from pathlib import Path
import argparse
import shutil

# Correct imports for MoviePy 2.x
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose images and audio into an MP4 video")
    parser.add_argument("--audio", type=str, help="Path to MP3/WAV audio file")
    parser.add_argument("--images", type=str, help="Folder containing images (.jpg/.png)")
    parser.add_argument("--output", type=str, help="Output MP4 path")
    parser.add_argument("--seconds", type=float, default=3.0, help="Seconds per image (default: 3.0)")
    parser.add_argument("--fps", type=int, default=24, help="Output frames per second (default: 24)")
    return parser.parse_args()


def main():
    # Defaults (preserved) with env overrides
    DEFAULT_AUDIO = Path("scripts/generated_audio/Sanatan_Dharma_principles.mp3")
    DEFAULT_IMAGES = Path("scripts/images")
    DEFAULT_OUTPUT = Path("scripts/final_video.mp4")

    args = parse_args()

    audio_env = os.environ.get("AIYT_AUDIO")
    images_env = os.environ.get("AIYT_IMAGES")
    output_env = os.environ.get("AIYT_OUTPUT")

    audio_path = Path(args.audio or audio_env or DEFAULT_AUDIO)
    images_folder = Path(args.images or images_env or DEFAULT_IMAGES)
    output_path = Path(args.output or output_env or DEFAULT_OUTPUT)
    seconds_per_image = float(args.seconds or 3.0)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not images_folder.exists():
        raise FileNotFoundError(f"Images directory not found: {images_folder}")

    # Verify ffmpeg availability to avoid silent failures
    ffmpeg_bin = shutil.which("ffmpeg") or os.environ.get("FFMPEG_BINARY")
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg not found. Install FFmpeg and ensure 'ffmpeg' is on PATH or set FFMPEG_BINARY.")

    # Load images (supports .jpg, .png, and .jpg.png)
    images = sorted(images_folder.glob("*.jpg")) + sorted(images_folder.glob("*.png")) + sorted(images_folder.glob("*.jpg.png"))
    images = sorted(set(images))
    if not images:
        raise ValueError("No images found in the specified images directory.")

    print(f"Composing {len(images)} images at {seconds_per_image}s each...")
    clips = [ImageClip(str(img)).with_duration(seconds_per_image) for img in images]

    # Concatenate images
    video = concatenate_videoclips(clips, method="compose")

    # Add audio
    audio = AudioFileClip(str(audio_path))
    video = video.with_audio(audio).with_duration(audio.duration)

    try:
        # Ensure output directory exists
        os.makedirs(output_path.parent, exist_ok=True)

        # Remove old file if exists
        if output_path.exists():
            os.remove(output_path)

        print(f"Rendering to {output_path} (fps={args.fps})...")
        video.write_videofile(
            str(output_path),
            fps=int(args.fps),
            codec="libx264",
            audio_codec="aac"
        )
        print(f"Video saved: {output_path}")
    finally:
        # Clean up resources
        video.close()
        audio.close()
        for clip in clips:
            clip.close()


if __name__ == "__main__":
    main()
