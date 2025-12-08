from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, Request
from app.db import get_conn
from app.auth.security import get_current_user
from app.templates.schema import normalize_plan, validate_plan
from app.templates.vars import parse_vars as _parse_vars, apply_vars as _apply_vars
from routes.render import RenderPlan  # reuse pydantic model for validation
from backend.app.usage.service import check_quota_or_raise, inc_renders
from backend.app.db import enqueue_job
from datetime import datetime
import json
import uuid

router = APIRouter(prefix="/templates", tags=["templates"])

@router.get("/builtin")
def list_builtin_templates():
    """Return only builtin templates (visibility='builtin')."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, description, category, thumb, plan_json, inputs_schema, visibility, user_id FROM templates WHERE visibility='builtin' ORDER BY title ASC"
        ).fetchall()
        def row_to_dict(r):
            return {k: r[k] for k in r.keys()}
        return {"templates": [row_to_dict(r) for r in rows]}
    finally:
        conn.close()


def _get_template(conn, template_id: str):
    row = conn.execute(
        "SELECT id, title, description, category, thumb, plan_json, inputs_schema, visibility, user_id FROM templates WHERE id=?",
        (template_id,),
    ).fetchone()
    return row


def _assert_owner_or_builtin(row, user):
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    if row["visibility"] == "builtin":
        return
    if not user or row["user_id"] != user.get("id"):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/{template_id}")
def get_template_meta(template_id: str, user=Depends(get_current_user)):
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        _assert_owner_or_builtin(row, user)
        return {k: row[k] for k in row.keys()}
    finally:
        conn.close()


@router.get("/{template_id}/plan")
def get_template_plan(template_id: str, user=Depends(get_current_user)):
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        _assert_owner_or_builtin(row, user)
        plan_raw = row["plan_json"] or "{}"
        try:
            plan_dict = json.loads(plan_raw)
        except Exception:
            plan_dict = {}
        return normalize_plan(plan_dict)
    finally:
        conn.close()


@router.put("/{template_id}/plan")
def put_template_plan(template_id: str, payload: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        if row["visibility"] == "builtin":
            raise HTTPException(status_code=403, detail="Builtin templates are read-only")
        if row["user_id"] != user.get("id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        plan = normalize_plan(payload or {})
        warnings = validate_plan(plan)
        conn.execute(
            "UPDATE templates SET plan_json=? WHERE id=?",
            (json.dumps(plan, ensure_ascii=False), template_id),
        )
        conn.commit()
        return {"plan": plan, "warnings": warnings}
    finally:
        conn.close()


@router.get("/{template_id}/vars")
def get_template_vars(template_id: str, user=Depends(get_current_user)):
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        _assert_owner_or_builtin(row, user)
        raw = row["plan_json"] or "{}"
        try:
            plan = json.loads(raw)
        except Exception:
            plan = {}
        vars_set = sorted(list(_parse_vars(plan)))
        schema = None
        if row["inputs_schema"]:
            try:
                schema = json.loads(row["inputs_schema"])  # type: ignore[assignment]
            except Exception:
                schema = None
        return {"vars": vars_set, "inputs_schema": schema}
    finally:
        conn.close()


@router.patch("/{template_id}/inputs-schema")
def patch_template_inputs_schema(template_id: str, payload: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        if row["visibility"] == "builtin":
            raise HTTPException(status_code=403, detail="Builtin templates are read-only")
        if row["user_id"] != user.get("id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        schema = payload or {}
        try:
            schema_json = json.dumps(schema, ensure_ascii=False)
        except Exception:
            raise HTTPException(status_code=422, detail="inputs_schema must be JSON-serializable")
        conn.execute("UPDATE templates SET inputs_schema=? WHERE id=?", (schema_json, template_id))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/{template_id}/preview-plan")
def preview_template_plan(template_id: str, payload: dict, user=Depends(get_current_user)):
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        _assert_owner_or_builtin(row, user)
        base_raw = row["plan_json"] or "{}"
        try:
            base_plan = json.loads(base_raw)
        except Exception:
            base_plan = {}
        # Normalize then apply variables
        norm = normalize_plan(base_plan)
        inputs = payload.get("inputs") if isinstance(payload, dict) else None
        applied, var_warnings = _apply_vars(norm, inputs if isinstance(inputs, dict) else {})
        # Re-validate after substitution (non-fatal)
        warnings = (validate_plan(applied) or []) + (var_warnings or [])
        return {"plan": applied, "warnings": warnings}
    finally:
        conn.close()


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@router.post("/{template_id}/render")
def render_from_template(template_id: str, payload: dict | None, request: Request, user=Depends(get_current_user)):
    # Ownership or builtin access
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        _assert_owner_or_builtin(row, user)
    finally:
        conn.close()

    if user:
        # Enforce one render quota increment
        check_quota_or_raise(user["id"], add_renders=1)

    # Load and resolve plan
    try:
        base = json.loads(row["plan_json"]) if row["plan_json"] else {}
    except Exception:
        base = {}
    norm = normalize_plan(base)
    inputs = (payload or {}).get("inputs") if isinstance(payload, dict) else None
    overrides = (payload or {}).get("overrides") if isinstance(payload, dict) else None
    resolved, _ = _apply_vars(norm, inputs if isinstance(inputs, dict) else {})
    if isinstance(overrides, dict):
        resolved = _deep_merge(resolved, overrides)

    # Map to RenderPlan schema
    scenes = []
    for s in resolved.get("scenes", []) or []:
        if not isinstance(s, dict):
            continue
        scenes.append({
            "image_prompt": s.get("image_prompt") or "",
            "narration": s.get("script") or "",
            "duration_sec": s.get("duration_sec") or 2,
        })
    render_payload = {
        "topic": resolved.get("title") or "Generated Video",
        "language": "en",
        "voice": "F",
        "voice_id": resolved.get("voice_id") or None,
        "scenes": scenes,
        "fast_path": True,
        "proxy": True,
        "quality": "final",
    }
    # Validate via Pydantic
    plan_model = RenderPlan(**render_payload)
    plan_dict = plan_model.model_dump(mode="python")

    # Create job and persist lineage
    job_id = str(uuid.uuid4())
    plan_dict["job_id"] = job_id
    title = str(plan_dict.get("topic") or "Video")
    parent_job_id = f"tpl:{template_id}"
    try:
        conn = get_conn()
        try:
            now = datetime.utcnow().isoformat()
            conn.execute(
                (
                    "INSERT OR IGNORE INTO jobs_index (id, user_id, project_id, title, created_at, input_json, parent_job_id) "
                    "VALUES (?,?,?,?,?,?,?)"
                ),
                (job_id, user["id"] if user else "", (payload or {}).get("project_id"), title, now, json.dumps(plan_dict), parent_job_id),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    enqueue_job(job_id, user["id"] if user else "", json.dumps(plan_dict))
    if user:
        try:
            inc_renders(user["id"], 1)
        except Exception:
            pass
    return {"job_id": job_id, "status": "queued", "parent_job_id": parent_job_id}


@router.post("")
def create_template(payload: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    title = (payload.get("title") or "Untitled").strip()
    description = payload.get("description")
    category = payload.get("category")
    thumb = payload.get("thumb")
    visibility = payload.get("visibility") or "private"
    plan_in = payload.get("plan_json") or {}
    plan = normalize_plan(plan_in if isinstance(plan_in, dict) else {})
    warnings = validate_plan(plan)
    tpl_id = payload.get("id") or str(uuid.uuid4())
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO templates (id, title, description, category, thumb, plan_json, inputs_schema, visibility, user_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (tpl_id, title, description, category, thumb, json.dumps(plan, ensure_ascii=False), None, visibility, user["id"]),
        )
        conn.commit()
        row = _get_template(conn, tpl_id)
        data = {k: row[k] for k in row.keys()}
        data["warnings"] = warnings
        return data
    finally:
        conn.close()


@router.patch("/{template_id}")
def patch_template(template_id: str, payload: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        row = _get_template(conn, template_id)
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        if row["visibility"] == "builtin":
            raise HTTPException(status_code=403, detail="Builtin templates are read-only")
        if row["user_id"] != user.get("id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        fields = []
        values = []
        for k in ("title", "description", "category", "thumb", "visibility"):
            if k in payload:
                fields.append(f"{k}=?")
                values.append(payload.get(k))
        if "inputs_schema" in payload:
            try:
                schema_json = json.dumps(payload.get("inputs_schema"), ensure_ascii=False)
            except Exception:
                raise HTTPException(status_code=422, detail="inputs_schema must be JSON-serializable")
            fields.append("inputs_schema=?")
            values.append(schema_json)
        warnings = []
        if "plan_json" in payload:
            plan_in = payload.get("plan_json") or {}
            plan = normalize_plan(plan_in if isinstance(plan_in, dict) else {})
            warnings = validate_plan(plan)
            fields.append("plan_json=?")
            values.append(json.dumps(plan, ensure_ascii=False))
        if fields:
            values.append(template_id)
            conn.execute(f"UPDATE templates SET {', '.join(fields)} WHERE id=?", tuple(values))
            conn.commit()
        row2 = _get_template(conn, template_id)
        data = {k: row2[k] for k in row2.keys()}
        if warnings:
            data["warnings"] = warnings
        return data
    finally:
        conn.close()
