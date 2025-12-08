import os
import json
import argparse
from pathlib import Path
import openai


def load_api_key() -> str:
    # Prefer environment variable; fallback to config/api_keys.json
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key
    cfg_path = Path("config/api_keys.json")
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            key = data.get("OPENAI_API_KEY") or data.get("openai")
            if key:
                return key
        except Exception:
            pass
    raise RuntimeError("OPENAI_API_KEY not set. Set env var or add to config/api_keys.json")


def sanitize_filename(topic: str) -> str:
    name = topic.strip().replace(" ", "_")
    # Basic sanitization: keep alphanum, _ and -
    return "".join(c for c in name if c.isalnum() or c in ("_", "-")) or "script"


def generate_script_text(topic: str) -> str:
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a YouTube script generator"},
            {"role": "user", "content": f"Write a concise, engaging YouTube Shorts script about: {topic}. Keep it under 150 words, with a hook and clear takeaway."},
        ],
    )
    return response.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser(description="Generate a YouTube script using OpenAI and save to file")
    parser.add_argument("topic", type=str, nargs="?", help="Topic for the script (e.g., 'Sanatan Dharma principles')")
    args = parser.parse_args()

    topic = args.topic or input("Enter topic: ").strip()
    if not topic:
        raise ValueError("Topic is required")

    openai.api_key = load_api_key()

    text = generate_script_text(topic)
    out_dir = Path("scripts/generated_scripts")
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = sanitize_filename(topic) + ".txt"
    out_path = out_dir / fname
    out_path.write_text(text, encoding="utf-8")
    print(f"Script saved: {out_path}")


if __name__ == "__main__":
    main()
