import type { Plan, Scene } from '@/types/plan';

export function SceneEditor({ plan, onChange, disabled = false }: { plan: Plan; onChange: (p: Plan) => void; disabled?: boolean }) {
  const updateScene = (idx: number, patch: Partial<Scene>) => {
    const scenes = [...(plan.scenes ?? [])];
    scenes[idx] = { ...scenes[idx], ...patch };
    onChange({ ...plan, scenes });
  };
  const addScene = () => onChange({ ...plan, scenes: [...(plan.scenes ?? []), { script: '', image_prompt: '', duration_sec: 2 }] });
  const duplicate = (idx: number) => {
    const scenes = [...(plan.scenes ?? [])];
    scenes.splice(idx + 1, 0, { ...(scenes[idx] || {}) });
    onChange({ ...plan, scenes });
  };
  const remove = (idx: number) => {
    const scenes = [...(plan.scenes ?? [])];
    scenes.splice(idx, 1);
    onChange({ ...plan, scenes });
  };
  const move = (idx: number, dir: -1 | 1) => {
    const scenes = [...(plan.scenes ?? [])];
    const j = idx + dir;
    if (j < 0 || j >= scenes.length) return;
    const tmp = scenes[idx];
    scenes[idx] = scenes[j];
    scenes[j] = tmp;
    onChange({ ...plan, scenes });
  };

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <button disabled={disabled} onClick={addScene}>Add Scene</button>
      </div>
      {(plan.scenes ?? []).map((s, i) => (
        <div key={i} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginBottom: 8 }}>
            <button disabled={disabled} onClick={() => duplicate(i)}>Duplicate</button>
            <button disabled={disabled} onClick={() => move(i, -1)}>Move Up</button>
            <button disabled={disabled} onClick={() => move(i, 1)}>Move Down</button>
            <button disabled={disabled} onClick={() => remove(i)}>Delete</button>
          </div>
          <label style={{ display: 'grid', gap: 4, marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Script</span>
            <textarea disabled={disabled} rows={3} value={s.script ?? ''} onChange={(e) => updateScene(i, { script: e.target.value })} />
          </label>
          <label style={{ display: 'grid', gap: 4, marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Image Prompt</span>
            <textarea disabled={disabled} rows={2} value={s.image_prompt ?? ''} onChange={(e) => updateScene(i, { image_prompt: e.target.value })} />
          </label>
          <label style={{ display: 'grid', gap: 4, width: 160 }}>
            <span style={{ fontSize: 12, color: '#6b7280' }}>Duration (sec)</span>
            <input disabled={disabled} type="number" step="0.1" value={s.duration_sec ?? 2} onChange={(e) => updateScene(i, { duration_sec: Number(e.target.value) })} />
          </label>
        </div>
      ))}
    </div>
  );
}
