from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from routes.render import RenderPlan, SceneInput

router = APIRouter(prefix="/storyboard", tags=["storyboard"])


class StoryboardRequest(BaseModel):
    topic: str = Field(..., min_length=3)
    duration_sec: float = Field(default=60.0, gt=0)
    voice: str = Field(default="F", pattern="^(F|M)$")
    style: str = Field(default="calm temple")
    language: str = Field(default="hi")


def _build_scenes(req: StoryboardRequest) -> List[SceneInput]:
    total = float(req.duration_sec) if req.duration_sec else 60.0
    scene_count = min(6, max(4, int(round(total / 20)) or 4))
    minimum_total = scene_count * 0.5
    if total < minimum_total:
        total = minimum_total
    base = total / scene_count
    durations: List[float] = [round(base, 2) for _ in range(scene_count)]
    # Adjust last element to ensure sum matches requested total
    durations[-1] = round(total - sum(durations[:-1]), 2)

    prompts = [
        f"{req.style} {req.topic} opening",
        f"{req.style} {req.topic} insight",
        f"{req.style} {req.topic} reflection",
        f"{req.style} {req.topic} practice",
        f"{req.style} {req.topic} blessing",
        f"{req.style} {req.topic} closing",
    ]

    scenes: List[SceneInput] = []
    for idx in range(scene_count):
        prompt_text = prompts[idx] if idx < len(prompts) else f"{req.style} {req.topic} detail {idx + 1}"
        narration_text = f"{req.topic} scene {idx + 1} in {req.language}"
        scenes.append(
            SceneInput(
                image_prompt=prompt_text,
                narration=narration_text,
                duration_sec=durations[idx],
            )
        )
    return scenes


@router.post("/generate")
def generate_storyboard(req: StoryboardRequest) -> dict:
    scenes = _build_scenes(req)
    plan = RenderPlan(
        topic=req.topic,
        language=req.language,
        voice=req.voice,
        scenes=scenes,
        fast_path=True,
        proxy=True,
        enable_parallax=True,
        enable_templates=True,
        enable_audio_sync=True,
        quality="final",
    )
    plan_dict = plan.dict()
    plan_dict["style"] = req.style
    plan_dict["duration_sec"] = req.duration_sec
    return plan_dict
