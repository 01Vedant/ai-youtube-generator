import { useEffect, useMemo, useState } from 'react';
import type { InputsSchema } from '@/types/plan';

type ExtendedField = InputsSchema[string];

type Props = {
  vars: string[];
  schema?: InputsSchema;
  onPreview: (inputs: Record<string, unknown>) => Promise<{ warnings?: string[] } | void> | void;
  onRender: (inputs: Record<string, unknown>) => Promise<void> | void;
  initial?: Record<string, unknown>;
};

export function TemplateQuickFill({ vars, schema, onPreview, onRender, initial }: Props) {
  const [inputs, setInputs] = useState<Record<string, unknown>>(initial || {});
  const [warnings, setWarnings] = useState<string[]>([]);
  const orderedVars = useMemo(() => {
    const withSchema = vars.filter((v) => schema && schema[v]);
    const withoutSchema = vars.filter((v) => !schema || !schema[v]);
    return [...withSchema, ...withoutSchema];
  }, [vars, schema]);

  useEffect(() => {
    if (!initial) return;
    setInputs((i) => ({ ...initial, ...i }));
  }, [initial]);

  const change = (key: string, value: unknown) => setInputs((prev) => ({ ...prev, [key]: value }));

  const handlePreview = async () => {
    const res = await onPreview(inputs);
    if (res && res.warnings && res.warnings.length) setWarnings(res.warnings);
    else setWarnings([]);
  };

  const handleRender = async () => {
    await onRender(inputs);
  };

  return (
    <div>
      <div style={{ display: 'grid', gap: 12, marginTop: 8 }}>
        {orderedVars.map((v) => {
          const f = schema?.[v] as ExtendedField | undefined;
          const required = f?.required ?? false;
          const label = f?.label || f?.title || v;
          const placeholder = f?.placeholder || f?.description || '';
          if (f?.type === 'number') {
            return (
              <label key={v} style={{ display: 'grid', gap: 4 }}>
                <span style={{ fontSize: 12, color: '#6b7280' }}>{label}{required ? ' *' : ''}</span>
                <input type="number" value={(inputs[v] as number | undefined) ?? ''} onChange={(e) => change(v, Number(e.target.value))} placeholder={placeholder} />
              </label>
            );
          }
          if (f?.type === 'enum' && Array.isArray(f?.enum)) {
            return (
              <label key={v} style={{ display: 'grid', gap: 4 }}>
                <span style={{ fontSize: 12, color: '#6b7280' }}>{label}{required ? ' *' : ''}</span>
                <select value={(inputs[v] as string | undefined) ?? ''} onChange={(e) => change(v, e.target.value)}>
                  <option value="" disabled>Select</option>
                  {f.enum.map((opt) => (<option key={opt} value={opt}>{opt}</option>))}
                </select>
              </label>
            );
          }
          return (
            <label key={v} style={{ display: 'grid', gap: 4 }}>
              <span style={{ fontSize: 12, color: '#6b7280' }}>{label}{required ? ' *' : ''}</span>
              <input type="text" value={(inputs[v] as string | undefined) ?? ''} onChange={(e) => change(v, e.target.value)} placeholder={placeholder} />
            </label>
          );
        })}
      </div>

      {warnings.length > 0 && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: 8, borderRadius: 6, marginTop: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Warnings</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {warnings.map((w, i) => (<li key={i}>{w}</li>))}
          </ul>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button onClick={handlePreview}>Preview Plan</button>
        <button onClick={handleRender}>Render</button>
      </div>
    </div>
  );
}
