# Hindi TTS Path Shadowing Fix - Complete Implementation

## Changes Applied

### 1. Orchestrator Import Fix (Task 1)
**File**: `platform/orchestrator.py`

**Changes**:
- ✅ Removed sys.path manipulation that added `platform/` directory
- ✅ Added logging import and logger instance
- ✅ Direct imports: `from backend.app.settings import OUTPUT_ROOT`
- ✅ Added loud TTS diagnostics: `logger.info("[TTS] language=%s voice_id=%s provider=%s")`
- ✅ Enhanced exception handling with full stack traces
- ✅ Changed import from `backend.app.tts` to `backend.app.tts.engine` for clarity

**Root Cause Fixed**: The `platform/` directory was shadowing Python's built-in `platform` module, causing `edge_tts` → `aiohttp` → `multidict` import chain to fail with `AttributeError: module 'platform' has no attribute 'python_implementation'`

### 2. Audio Metadata Flow (Task 2)
**File**: `platform/routes/render.py`

**Changes**:
- ✅ Added `audio_error` pass-through from orchestrator summary to status response
- ✅ Status endpoint now includes both `audio` metadata and `audio_error` field
- ✅ RenderPlan already has `Optional[str] voice_id` and `language` fields with proper serialization

**File**: `platform/orchestrator.py`

**Changes**:
- ✅ Added `audio_error` variable to track TTS failures
- ✅ Summary now includes `audio_error` field when TTS fails
- ✅ Mock audio metadata always set on Hindi fallback (critical for E2E testing)

### 3. Hindi Branch Guaranteed Execution (Task 3)
**File**: `platform/orchestrator.py`

**Changes**:
- ✅ Hindi TTS path (`if language == "hi"`) now ALWAYS sets audio metadata
- ✅ On exception: generates silent WAV placeholders via `tiny_wav(3.0)`
- ✅ Fallback audio metadata includes: `provider="mock"`, `paced=False`, error tracked separately
- ✅ Logger captures full stack trace for debugging

### 4. TTS Health Check Endpoint (Task 4)
**File**: `platform/backend/app/main.py`

**Added**: `/debug/tts` endpoint
```python
@app.get("/debug/tts")
async def debug_tts():
    # Returns: provider, default_voice, voices[], health status
```

**File**: `platform/backend/app/tts/engine.py`

**Added**: `health_check()` function
- ✅ Verifies edge-tts and aiohttp imports
- ✅ Returns `ok: True/False` with detailed reason
- ✅ Version information when available

**File**: `platform/backend/app/tts/__init__.py`

**Updated**: Export `health_check` function

### 5. Restart Scripts (Task 5)
**File**: `scripts/dev-start.ps1` (NEW)

**Features**:
- Stops existing python/uvicorn processes
- Sets environment: `SIMULATE_RENDER=1`, `DEV_FAST=1`
- Starts uvicorn on http://127.0.0.1:8000

**File**: `scripts/smoke_tts_hi_frontend.ps1`

**Already Updated**:
- ✅ UTF-8 encoding for Hindi text
- ✅ Correct request schema (image_prompt, duration_sec)
- ✅ Strict audio metadata assertions

### 6. Frontend Error Surfacing (Task 6)
**File**: `platform/frontend/src/pages/RenderStatusPage.tsx`

**Changes**:
- ✅ Added yellow badge for `provider="mock"`: "⚠️ Mock Voice"
- ✅ Added red badge for `audio_error`: "⚠️ TTS fallback (see logs)" with tooltip
- ✅ Badges only appear when `status.audio.lang === 'hi'`

### 7. Test Coverage (Bonus)
**File**: `platform/backend/tests/test_voice_id_roundtrip.py` (NEW)

**Features**:
- POST with `language='hi'`, `voice_id='hi-IN-SwaraNeural'`
- Poll /status until completion
- Assert: language, audio.lang, audio.voice_id, audio.provider all present

---

## Verification Steps

### Step 1: Restart Backend
```powershell
.\scripts\dev-start.ps1
```

### Step 2: Health Checks
```powershell
# Basic health
curl http://127.0.0.1:8000/healthz

# TTS diagnostic
curl http://127.0.0.1:8000/debug/tts
```

**Expected /debug/tts response**:
```json
{
  "ok": true,
  "provider": "edge",
  "default_voice": "hi-IN-SwaraNeural",
  "voices": ["hi-IN-SwaraNeural", "hi-IN-DiyaNeural", ...],
  "health": {"ok": true, "provider": "edge", "available": true}
}
```

### Step 3: Backend Smoke Test
```powershell
.\scripts\smoke_tts_hi_frontend.ps1
```

**Expected output**:
```
[1/5] Submitting Hindi render job...
[OK] Job created: <uuid>

[2/5] Polling for job completion...
  State: running
  State: completed
[OK] Job completed successfully

[3/5] Validating audio metadata...
  Lang: hi
  Voice ID: hi-IN-SwaraNeural
  Provider: edge (or mock if edge unavailable)
  Paced: True/False
[OK] Audio metadata validated

[4/5] Checking final video...
[OK] Final video accessible

[5/5] Test Summary
[SUCCESS] ALL TESTS PASSED
```

### Step 4: Unit Test
```powershell
cd platform/backend
python -m pytest tests/test_voice_id_roundtrip.py -v
```

### Step 5: Frontend Verification
1. Open http://localhost:5173/create
2. Click "🇮🇳 Use Hindi Sample"
3. Click "Preview TTS" on Scene 1
4. Verify audio plays
5. Submit render
6. Open status page
7. Verify badges appear:
   - "🇮🇳 Hindi • Swara (soothing) • Paced" (if successful)
   - "⚠️ Mock Voice" (if fallback)
   - "⚠️ TTS fallback (see logs)" (if audio_error present)

---

## Troubleshooting

### If audio is still null

**Check 1**: Branch execution
```powershell
# Find latest job
$jobId = (Get-ChildItem "platform/backend/pipeline_outputs" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name

# Check logs for [TTS] marker
Get-Content "platform/backend/pipeline_outputs/$jobId/job_summary.json" | ConvertFrom-Json | Select-Object -ExpandProperty logs | Where-Object { $_.message -like "*TTS*" }
```

**Check 2**: TTS health
```powershell
curl http://127.0.0.1:8000/debug/tts | ConvertFrom-Json
```

**Check 3**: No sys.path pollution
```powershell
# Search for sys.path in orchestrator
Get-Content platform/orchestrator.py | Select-String "sys.path"
# Should return EMPTY or only comments
```

**Check 4**: edge-tts availability
```powershell
cd platform/backend
python -c "import edge_tts,sys; print('edge_tts OK', sys.executable)"
```

**Check 5**: Plan language field
```powershell
Get-Content "platform/backend/pipeline_outputs/$jobId/job_summary.json" | ConvertFrom-Json | Select-Object -ExpandProperty plan | Select-Object language, voice_id
```

---

## Commit Messages

```bash
git add platform/orchestrator.py
git commit -m "fix(backend): remove path pollution; robust TTS diagnostics"

git add platform/routes/render.py platform/backend/app/tts/
git commit -m "feat(api): voice_id+language roundtrip; expose audio metadata"

git add platform/orchestrator.py
git commit -m "fix(tts): force Hindi path with robust fallback + meta"

git add platform/backend/app/main.py platform/backend/app/tts/engine.py
git commit -m "feat(debug): /debug/tts endpoint for quick checks"

git add scripts/
git commit -m "chore(scripts): restart helper + strict TTS smoke"

git add platform/frontend/src/pages/RenderStatusPage.tsx
git commit -m "feat(ui): surface TTS fallback and provider badges"

git add platform/backend/tests/test_voice_id_roundtrip.py
git commit -m "test(api): voice_id roundtrip integration test"
```

---

## Success Criteria

✅ `/debug/tts` returns `ok: true`  
✅ `smoke_tts_hi_frontend.ps1` shows "ALL TESTS PASSED"  
✅ `/status` response includes `audio.lang: "hi"`, `audio.voice_id: "hi-IN-..."`, `audio.provider`  
✅ Frontend badges display correctly (Hindi, Mock, or Fallback)  
✅ No `AttributeError: module 'platform' has no attribute` in logs  
✅ `test_voice_id_roundtrip.py` passes

---

## Files Modified Summary

| File | Changes | Lines |
|------|---------|-------|
| `platform/orchestrator.py` | Removed sys.path, added diagnostics, guaranteed Hindi fallback | ~40 |
| `platform/routes/render.py` | Added audio_error pass-through | ~5 |
| `platform/backend/app/main.py` | Added /debug/tts endpoint | ~25 |
| `platform/backend/app/tts/engine.py` | Added health_check() | ~45 |
| `platform/backend/app/tts/__init__.py` | Exported health_check | ~2 |
| `platform/frontend/src/pages/RenderStatusPage.tsx` | Added TTS fallback badges | ~15 |
| `scripts/dev-start.ps1` | NEW - Backend restart helper | ~30 |
| `platform/backend/tests/test_voice_id_roundtrip.py` | NEW - Roundtrip test | ~80 |

**Total**: 8 files, ~242 lines changed/added
