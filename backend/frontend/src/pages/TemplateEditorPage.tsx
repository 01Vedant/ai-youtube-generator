import { useCallback, useEffect, useState } from 'react';
import { getTemplatePlan, putTemplatePlan, submitRender, getTemplateVars, patchTemplateInputsSchema, previewTemplatePlan, renderFromTemplate } from '@/lib/api';
import type { Plan } from '@/types/plan';
import { useParams, useNavigate } from 'react-router-dom';
import { PlanHeaderForm } from '@/components/PlanHeaderForm';
import { SceneEditor } from '@/components/SceneEditor';
import { TemplateQuickFill } from '@/components/TemplateQuickFill';

export default function TemplateEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<Plan>({ scenes: [] });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [readonly, setReadonly] = useState(false);
  const [vars, setVars] = useState<string[]>([]);
  const [schemaJson, setSchemaJson] = useState<string>('');
  const [showQuickFill, setShowQuickFill] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        if (!id) return;
        // Meta to compute readonly
        const metaRes = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'}/templates/${id}`);
        const meta = await metaRes.json();
        setReadonly(meta?.visibility === 'builtin');
        const p = await getTemplatePlan(id);
        if (mounted) setPlan(p);
        // Load detected vars and inputs schema
        const v = await getTemplateVars(id);
        setVars(v.vars || []);
        setSchemaJson(v.inputs_schema ? JSON.stringify(v.inputs_schema, null, 2) : '{\n\n}');
      } catch (e) {
        // ignore
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (e.key.toLowerCase() === 's') {
        e.preventDefault();
        onSave();
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        onRender();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [plan, readonly]);

  const onSave = useCallback(async () => {
    if (!id || readonly) return;
    setSaving(true);
    try {
      const res = await putTemplatePlan(id, plan);
      setWarnings(res.warnings ?? []);
    } finally {
      setSaving(false);
    }
  }, [id, plan, readonly]);

  const onRender = useCallback(async () => {
    // Use existing /render from API
    try {
      const r = await submitRender(plan);
      navigate(`/render/${r.job_id}`);
    } catch (e) {
      // ignore
    }
  }, [plan]);

  if (loading) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0 }}>Template Editor</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setShowQuickFill(true)}>Quick Fill & Render</button>
          <button onClick={onRender}>Render Preview</button>
          <button disabled={readonly || saving} onClick={onSave}>{saving ? 'Saving…' : 'Save Plan'}</button>
        </div>
      </div>
      {readonly && (
        <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', padding: 12, borderRadius: 6, marginTop: 12 }}>
          Built-in template is read-only.
        </div>
      )}
      {warnings.length > 0 && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', padding: 12, borderRadius: 6, marginTop: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Warnings</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {warnings.map((w, i) => (<li key={i}>{w}</li>))}
          </ul>
        </div>
      )}
      <div style={{ marginTop: 16 }}>
        <PlanHeaderForm plan={plan} onChange={setPlan} disabled={readonly} />
        <SceneEditor plan={plan} onChange={setPlan} disabled={readonly} />
        <div style={{ marginTop: 16, border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>Variables</h3>
            <button disabled={readonly} onClick={async () => {
              if (!id) return;
              try {
                const parsed = JSON.parse(schemaJson);
                await patchTemplateInputsSchema(id, parsed);
              } catch (e) {
                alert('Invalid JSON for inputs schema');
              }
            }}>Save Inputs Schema</button>
          </div>
          <div style={{ color: '#6b7280', fontSize: 13, marginTop: 6 }}>Detected: {vars.length ? vars.join(', ') : '—'}</div>
          <label style={{ display: 'grid', gap: 6, marginTop: 8 }}>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Inputs Schema (JSON)</span>
            <textarea rows={8} value={schemaJson} onChange={(e) => setSchemaJson(e.target.value)} disabled={readonly} />
          </label>
        </div>
      </div>

      {showQuickFill && id && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)' }} onClick={() => setShowQuickFill(false)}>
          <div style={{ background: '#fff', maxWidth: 640, margin: '10vh auto', padding: 24, borderRadius: 8 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>Quick Fill</h3>
              <button onClick={() => setShowQuickFill(false)}>Close</button>
            </div>
            <TemplateQuickFill
              vars={vars}
              schema={(() => { try { return JSON.parse(schemaJson); } catch { return undefined; } })()}
              onPreview={async (inputs) => {
                const r = await previewTemplatePlan(id, inputs);
                return { warnings: r.warnings };
              }}
              onRender={async (inputs) => {
                const r = await renderFromTemplate(id, { inputs });
                navigate(`/render/${r.job_id}`);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
