"""generate_images.py

Produces per-scene high-resolution image prompts and optionally calls an image API.

This script does NOT call any API by default. It writes engine-ready prompt files for:
  - OpenAI Image/DALL·E style
  - Stable Diffusion / SDXL (txt2img) style
  - Runway / Pika style
  - Luma / 3D prompt notes

To enable automatic generation, add API keys as environment variables and implement the
call sections below for your chosen provider.
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
PLAN = BASE / 'prahlad_plan.json'
OUT = BASE

def make_engine_prompts(prompt_text: str):
    # DALL·E / OpenAI style
    openai_prompt = prompt_text + " --ar 16:9 --quality cinematic --vibrant --ultra-detailed --4k"

    # Stable Diffusion / SDXL style (concise, tokenized)
    sd_prompt = (
        "<lora:hd_details:0.6> " + prompt_text + ", ultra-detailed, 8k, cinematic lighting, photorealistic painting, "
        "Raja Ravi Varma style, Pahari miniature color palette, film grain:0.2"
    )

    # Runway / Pika wording (short + cinematic cues)
    runway_prompt = prompt_text + " | cinematic lighting | highly detailed | 4k | semi-realistic | animation-ready"

    # Luma / 3D notes
    luma_notes = "Use prompt for 3D background plate: high-res 4k image, separate layers for foreground subject and background; supply normal map and alpha for cloth/aura." \
                 + prompt_text

    return {
        'openai': openai_prompt,
        'sd': sd_prompt,
        'runway': runway_prompt,
        'luma': luma_notes
    }

def main():
    scenes = json.loads(PLAN.read_text(encoding='utf-8'))
    mapping = []
    for s in scenes:
        idx = s['scene_number']
        prompt = s['image_prompt']
        engines = make_engine_prompts(prompt)
        for k,v in engines.items():
            pfile = OUT / f'scene_{idx}_prompt_{k}.txt'
            pfile.write_text(v, encoding='utf-8')

        mapping.append({'scene': idx, 'prompts': {k: str(OUT / f'scene_{idx}_prompt_{k}.txt') for k in engines}})

    (OUT / 'image_prompts_map.json').write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote per-engine prompt files and image_prompts_map.json')

if __name__ == '__main__':
    main()
