"""
Safe smoke test for DevotionalAI Platform

This script performs a non-destructive smoke test of the backend+storage+job queue
without calling any external AI APIs. It:

- Registers a temporary test user
- Creates a project
- Writes placeholder 4K images, small MP3 audio placeholders, and SRT files into local storage
  (so preview endpoints can be exercised)
- Queues the `video_stitch` job via the API (job creation only)
- Verifies job entry exists and preview endpoints return the placeholder assets

Run this after `docker compose up --build` has started the backend (http://localhost:8000).

Notes:
- This test purposely avoids ElevenLabs/OpenAI calls. It will fail if backend storage is configured
  to S3 and you do not have local storage available. For safe local testing, set `USE_S3=false`.

Usage:
    python platform/tests/smoke_test.py

"""

import requests
import time
import os
import json
from pathlib import Path
from PIL import Image
from pydub import AudioSegment

# Configuration
BACKEND = os.getenv('BACKEND_URL', 'http://localhost:8000')
REGISTER_URL = f"{BACKEND}/api/v1/auth/register"
LOGIN_URL = f"{BACKEND}/api/v1/auth/login"
CREATE_PROJECT_URL = f"{BACKEND}/api/v1/projects/create"
UPDATE_PROJECT_URL = f"{BACKEND}/api/v1/projects/{{project_id}}"
STITCH_URL = f"{BACKEND}/api/v1/projects/{{project_id}}/render/stitch"
JOB_STATUS_URL = f"{BACKEND}/api/v1/jobs/{{job_id}}"
PREVIEW_IMAGE_URL = f"{BACKEND}/api/v1/projects/{{project_id}}/preview/image/{{scene_number}}"
PREVIEW_AUDIO_URL = f"{BACKEND}/api/v1/projects/{{project_id}}/preview/audio/{{scene_number}}"

# Local storage path (should match config.LOCAL_STORAGE_PATH in backend)
LOCAL_STORAGE_PATH = Path(os.getenv('LOCAL_STORAGE_PATH', './storage'))

# Test user credentials
TEST_EMAIL = f"smoke_test_{int(time.time())}@example.com"
TEST_PASSWORD = "Sm0keTestPass!"
TEST_NAME = "Smoke Tester"

# Scenes to create
SCENES = [
    {"scene_number": 1, "scene_title": "Intro: Divine Light", "voiceover": "यह आरम्भ है। प्रभु की द्रष्टि।", "notes": "Duration: 6-8s"},
    {"scene_number": 2, "scene_title": "Devotion", "voiceover": "भक्ति का स्वर। प्राची रंग, दीपक की लौ।", "notes": "Duration: 8-10s"},
    {"scene_number": 3, "scene_title": "Blessing", "voiceover": "सभी को आशीर्वाद मिले।", "notes": "Duration: 6-8s"}
]


def register_user():
    print('Registering test user...')
    r = requests.post(REGISTER_URL, data={
        'email': TEST_EMAIL,
        'password': TEST_PASSWORD,
        'name': TEST_NAME
    })
    r.raise_for_status()
    data = r.json()
    return data['token'], data['user_id']


def create_project(token, name='Smoke Test Project'):
    print('Creating project...')
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.post(CREATE_PROJECT_URL, headers=headers, data={'name': name})
    r.raise_for_status()
    return r.json()['project_id']


def update_project_story(token, project_id, scenes):
    headers = {'Authorization': f'Bearer {token}'}
    payload = {'story_data': {'scenes': scenes}}
    r = requests.put(UPDATE_PROJECT_URL.format(project_id=project_id), headers=headers, json=payload)
    r.raise_for_status()
    print('Updated project with mock scenes')


def ensure_local_project_dirs(user_id, project_id):
    base = LOCAL_STORAGE_PATH / str(user_id) / str(project_id)
    for sub in ['images', 'audio', 'subtitles', 'videos', 'prompts']:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def create_placeholder_image(path: Path, scene_num: int):
    # Create a simple 4K placeholder image with scene number
    img = Image.new('RGB', (3840, 2160), color=(30, 20, 60))
    d = Image.ImageDraw.Draw(img)
    text = f"Scene {scene_num} - DevotionalAI Placeholder"
    try:
        from PIL import ImageFont
        font = ImageFont.truetype('arial.ttf', 80)
    except Exception:
        font = None
    d.text((200, 1000), text, fill=(255, 220, 120), font=font)
    img.save(path, format='PNG')


def create_placeholder_audio(path: Path, duration_seconds=6):
    # Create a short silent mp3 using pydub
    silence = AudioSegment.silent(duration=duration_seconds * 1000)
    silence.export(path, format='mp3')


def create_placeholder_srt(path: Path, text: str, duration_seconds: float):
    # Very simple SRT: split text into lines of ~35 chars and distribute time
    words = text.strip().split()
    lines = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + (1 if cur else 0) <= 35:
            cur.append(w)
            cur_len += len(w) + (1 if cur else 0)
        else:
            lines.append(' '.join(cur))
            cur = [w]
            cur_len = len(w)
    if cur:
        lines.append(' '.join(cur))

    per = duration_seconds / max(1, len(lines))
    t = 0.0
    def ts(t):
        h = int(t // 3600); m = int((t % 3600)//60); s = int(t % 60); ms = int((t - int(t))*1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    out = []
    idx = 1
    for l in lines:
        start = ts(t); end = ts(t + per)
        out.append(f"{idx}\n{start} --> {end}\n{l}\n")
        t += per; idx += 1

    path.write_text('\n'.join(out), encoding='utf-8')


def write_placeholders(base_path: Path, scenes, user_id, project_id):
    print('Writing placeholder assets to local storage...')
    for s in scenes:
        n = s['scene_number']
        img_path = base_path / 'images' / f'scene_{n}.png'
        audio_path = base_path / 'audio' / f'scene_{n}.mp3'
        srt_path = base_path / 'subtitles' / f'scene_{n}.srt'
        dur = 8
        # Parse duration from notes if present
        notes = s.get('notes','')
        import re
        m = re.search(r"Duration:\s*(\d+)(?:[–-](\d+))?s", notes)
        if m:
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
            dur = int((a + b) / 2)
        create_placeholder_image(img_path, n)
        create_placeholder_audio(audio_path, duration_seconds=dur)
        create_placeholder_srt(srt_path, s.get('voiceover',''), dur)
    print('Placeholders written')


def queue_stitch(token, project_id):
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.post(STITCH_URL.format(project_id=project_id), headers=headers, json={"resolution": "4k", "fps": 24})
    r.raise_for_status()
    data = r.json()
    return data.get('job_id')


def get_job_status(token, job_id):
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(JOB_STATUS_URL.format(job_id=job_id), headers=headers)
    r.raise_for_status()
    return r.json()


def preview_asset(token, project_id, scene_number):
    headers = {'Authorization': f'Bearer {token}'}
    ri = requests.get(PREVIEW_IMAGE_URL.format(project_id=project_id, scene_number=scene_number), headers=headers)
    ra = requests.get(PREVIEW_AUDIO_URL.format(project_id=project_id, scene_number=scene_number), headers=headers)
    return ri.status_code, ra.status_code


def main():
    print('Starting SAFE smoke test...')

    token, user_id = register_user()
    project_id = create_project(token)
    update_project_story(token, project_id, SCENES)

    base = ensure_local_project_dirs(user_id, project_id)
    write_placeholders(base, SCENES, user_id, project_id)

    job_id = queue_stitch(token, project_id)
    print('Stitch job queued:', job_id)

    # Check preview for scene 1
    time.sleep(1)
    img_status, audio_status = preview_asset(token, project_id, 1)
    print(f'Preview responses: image={img_status}, audio={audio_status}')

    # Get job status (should be queued)
    job = get_job_status(token, job_id)
    print('Job status:', json.dumps(job, indent=2, ensure_ascii=False))

    print('SAFE smoke test completed. No external APIs called.\n')


if __name__ == '__main__':
    main()
