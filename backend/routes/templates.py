"""
Templates route: GET /templates, POST /templates/plan
Provides preset Bhakti video templates with plan builder.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jobs.types import RenderPlan, SceneInput
from utils.transliterate import normalize_title, sanitize_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["templates"])


class Template(BaseModel):
    """Preset video template."""
    id: str
    title: str
    description: str
    topic: str
    default_language: str = "en"
    default_voice: str = "F"
    default_style: str = "cinematic"
    default_length: int = 60
    scenes_template: List[dict]
    tags: List[str] = []


class TemplatePlanRequest(BaseModel):
    """Request to build a RenderPlan from template."""
    template_id: str
    language: str = Field("en", pattern="^(en|hi)$")
    length_sec: int = Field(60, ge=10, le=600)
    voice: str = Field("F", pattern="^(F|M)$")
    style_ref: Optional[str] = None
    custom_topic: Optional[str] = None


# Preset Bhakti templates
TEMPLATES: dict[str, Template] = {
    "prahlad": Template(
        id="prahlad",
        title="Prahlad Charitram",
        description="Epic story of Prahlad, the devoted disciple of Bhagwan Vishnu",
        topic="Prahlad Charitram: The devotion of Prahlad and protection of the righteous",
        default_language="en",
        default_voice="M",
        default_style="epic",
        default_length=120,
        scenes_template=[
            {
                "prompt": "Ancient Hindu temple, golden architecture, lotus flowers, devotional atmosphere",
                "narration": "In the great epic of Bhagavata Purana, we encounter the story of Prahlad, the most devoted of Bhagwan Vishnu's followers.",
            },
            {
                "prompt": "Daitya kingdom, Hiranyakashipu's palace, dark stone, throne room",
                "narration": "Born to the demon king Hiranyakashipu, Prahlad refused to follow his father's ways and instead devoted his life to Bhagwan Vishnu.",
            },
            {
                "prompt": "Young boy in prayer, holy fire, sacred mantras, divine light",
                "narration": "Despite countless trials and torments, Prahlad's faith never wavered. He chanted the name of Bhagwan with unwavering devotion.",
            },
            {
                "prompt": "Narasimha avatar, half-man half-lion, divine fury, golden light",
                "narration": "When Hiranyakashipu sought to destroy his own son, Bhagwan manifested as Narasimha to protect his devout follower.",
            },
        ],
        tags=["devotion", "bhagavata", "vishnu", "epic"],
    ),
    "ganga_avatar": Template(
        id="ganga_avatar",
        title="Ganga Avatar: The Divine River",
        description="Sacred story of River Ganga's descent from heaven to earth",
        topic="Ganga Avatar: Divine descent of the sacred river for humanity's salvation",
        default_language="en",
        default_voice="F",
        default_style="spiritual",
        default_length=90,
        scenes_template=[
            {
                "prompt": "Himalayan peaks, eternal snow, sacred mountains, divine light",
                "narration": "In the ancient tales of our scriptures, we learn of Ganga, the most sacred and divine of all rivers.",
            },
            {
                "prompt": "Brahma's palace in heaven, celestial beings, cosmic dance",
                "narration": "Originally dwelling in the heavenly realms, Ganga was persuaded by the tapasya of King Bhagiratha to descend to Earth.",
            },
            {
                "prompt": "Shiva meditating in Kailash, matted hair, cosmic energy",
                "narration": "Realizing the danger her descent would pose, Bhagwan Shiva offered to break her fall with his locks.",
            },
            {
                "prompt": "Flowing sacred river, ghats, temples, pilgrims bathing",
                "narration": "Thus blessed, Ganga flows eternally, purifying all who touch her waters and delivering souls to liberation.",
            },
        ],
        tags=["sacred", "river", "shiva", "purification"],
    ),
    "hanuman_chalisa": Template(
        id="hanuman_chalisa",
        title="Hanuman Chalisa: 40 Verses of Devotion",
        description="Beautiful exposition of the Hanuman Chalisa, the 40 verses dedicated to Lord Hanuman",
        topic="Hanuman Chalisa: The path of unwavering devotion and service to Rama",
        default_language="hi",
        default_voice="M",
        default_style="meditative",
        default_length=180,
        scenes_template=[
            {
                "prompt": "Ancient forest, sacred monkeys, spiritual energy, moonlight",
                "narration": "जय हनुमान ज्ञान गुण सागर। In the hearts of millions, Hanuman Chalisa remains the most beloved hymn.",
            },
            {
                "prompt": "Hanuman sitting in devotion, tail forming Om symbol, golden light",
                "narration": "These forty verses celebrate the strength, devotion, and unwavering faith of Lord Hanuman.",
            },
            {
                "prompt": "Rama and Sita in kingdom, Hanuman serving, devotional atmosphere",
                "narration": "Through Hanuman's example, we learn the highest form of devotion: selfless service without expectation.",
            },
        ],
        tags=["devotion", "hanuman", "chalisa", "rama"],
    ),
}


@router.get("/templates")
async def list_templates() -> dict:
    """
    GET /templates
    Return list of available preset templates.
    """
    templates_list = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "topic": t.topic,
            "tags": t.tags,
        }
        for t in TEMPLATES.values()
    ]
    logger.info("Listed %d templates", len(templates_list))
    return {
        "templates": templates_list,
        "total": len(templates_list),
    }


@router.post("/templates/plan")
async def build_plan_from_template(req: TemplatePlanRequest) -> RenderPlan:
    """
    POST /templates/plan
    Build a fully-formed RenderPlan from a template with customizations.
    
    Query parameters:
        template_id: ID of template (e.g., 'prahlad', 'ganga_avatar', 'hanuman_chalisa')
        language: 'en' or 'hi'
        length_sec: Target video length in seconds (10-600)
        voice: 'F' or 'M'
        style_ref: Optional style reference
        custom_topic: Optional override for topic
    """
    if req.template_id not in TEMPLATES:
        logger.warning("Template not found: %s", req.template_id)
        raise HTTPException(
            status_code=404,
            detail=f"Template '{req.template_id}' not found. Available: {', '.join(TEMPLATES.keys())}",
        )
    
    template = TEMPLATES[req.template_id]
    
    # Use custom topic if provided, else use template's topic
    topic = sanitize_text(req.custom_topic, max_length=500) if req.custom_topic else template.topic
    
    # Build scenes, scaling duration based on target length
    scenes_data = template.scenes_template
    num_scenes = len(scenes_data)
    target_duration_per_scene = req.length_sec / num_scenes if num_scenes > 0 else req.length_sec
    
    scenes: List[SceneInput] = []
    for scene_template in scenes_data:
        # Ensure text is sanitized
        prompt = sanitize_text(scene_template.get("prompt", ""), max_length=500)
        narration = sanitize_text(scene_template.get("narration", ""), max_length=1000)
        
        scene = SceneInput(
            prompt=prompt,
            narration=narration,
            duration=int(target_duration_per_scene),
        )
        scenes.append(scene)
    
    # Build render plan
    plan = RenderPlan(
        topic=normalize_title(topic),
        language=req.language,
        voice=req.voice,
        length=req.length_sec,
        style=req.style_ref or template.default_style,
        scenes=scenes,
        images_per_scene=3,
        burn_in_subtitles=True,
        upload_to_cloud=True,
    )
    
    logger.info(
        "Built plan from template %s: topic=%s, language=%s, %d scenes, %d sec",
        req.template_id, topic, req.language, len(scenes), req.length_sec
    )
    
    return plan
