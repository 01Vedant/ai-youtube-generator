import os
from pathlib import Path
import argparse
import pyttsx3


def sanitize_filename(name: str) -> str:
    n = name.strip().replace(" ", "_")
    return "".join(c for c in n if c.isalnum() or c in ("_", "-")) or "audio"


def text_to_audio_pyttsx3(text: str, topic: str, rate: int = 180) -> Path:
    out_dir = Path("scripts/generated_audio")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sanitize_filename(topic)}.mp3"

    engine = pyttsx3.init()
    try:
        engine.setProperty('rate', rate)
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
    finally:
        engine.stop()

    return out_path


def main():
    parser = argparse.ArgumentParser(description="Convert a generated script to speech using pyttsx3")
    parser.add_argument("topic", type=str, nargs="?", help="Topic name (used for output filename)")
    parser.add_argument("script_file", type=str, nargs="?", help="Filename in scripts/generated_scripts (e.g., Sanatan_Dharma.txt)")
    args = parser.parse_args()

    topic = args.topic or input("Enter topic: ").strip()
    script_file = args.script_file or input("Enter script filename (in scripts/generated_scripts): ").strip()

    if not topic:
        raise ValueError("Topic is required")
    if not script_file:
        raise ValueError("Script filename is required")

    script_path = Path("scripts/generated_scripts") / script_file
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    text = script_path.read_text(encoding="utf-8")
    out_path = text_to_audio_pyttsx3(text, topic)
    print(f"Audio saved: {out_path}")


if __name__ == "__main__":
    main()
