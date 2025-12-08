import type { Plan } from '@/types/plan';

export function PlanHeaderForm({ plan, onChange, disabled = false }: { plan: Plan; onChange: (p: Plan) => void; disabled?: boolean }) {
  const set = (k: keyof Plan, v: any) => onChange({ ...plan, [k]: v });
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 12 }}>
      <label style={{ display: 'grid', gap: 4 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Title</span>
        <input disabled={disabled} value={plan.title ?? ''} onChange={(e) => set('title', e.target.value)} />
      </label>
      <label style={{ display: 'grid', gap: 4 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Voice ID</span>
        <input disabled={disabled} value={plan.voice_id ?? ''} onChange={(e) => set('voice_id', e.target.value)} />
      </label>
      <label style={{ display: 'grid', gap: 4 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Template</span>
        <input disabled={disabled} value={plan.template ?? ''} onChange={(e) => set('template', e.target.value)} />
      </label>
      <label style={{ display: 'grid', gap: 4 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Duration (sec)</span>
        <input disabled={disabled} type="number" step="0.1" value={plan.duration_sec ?? 0} onChange={(e) => set('duration_sec', Number(e.target.value))} />
      </label>
    </div>
  );
}
