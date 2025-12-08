from pathlib import Path
import os
import uuid
import logging
from typing import List

logger = logging.getLogger(__name__)


class ImageEngine:
    def __init__(self, output_dir: Path, size=(3840, 2160)):
        self.output_dir = Path(output_dir)
        self.size = size
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _openai_available(self):
        try:
            import openai
            return True
        except Exception:
            return False

    def generate(self, scene_id: str, prompt: str, count: int = 1) -> List[Path]:
        out_paths = []
        for i in range(count):
            fname = f"{scene_id}-{i}-{uuid.uuid4().hex}.png"
            out = self.output_dir / fname
            if os.environ.get("OPENAI_API_KEY") and self._openai_available():
                try:
                    import openai
                    resp = openai.Image.create(prompt=prompt, size=f"{self.size[0]}x{self.size[1]}")
                    b64 = resp["data"][0]["b64_json"]
                    import base64
                    img = base64.b64decode(b64)
                    out.write_bytes(img)
                    out_paths.append(out)
                    continue
                except Exception as e:
                    logger.warning("OpenAI image generation failed: %s", e)
            try:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new("RGB", self.size, color=(30, 30, 30))
                draw = ImageDraw.Draw(img)
                text = (prompt[:200] + "...") if len(prompt) > 200 else prompt
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                draw.text((50, 50), text, fill=(230, 230, 230), font=font)
                img.save(out, format="PNG")
                out_paths.append(out)
            except Exception as e:
                logger.exception("PIL placeholder image generation failed: %s", e)
        return out_paths
