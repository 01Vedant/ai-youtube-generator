import { useEffect, useState } from 'react';
import { getBuiltinTemplates, type TemplateItem, getTemplateVars, previewTemplatePlan, renderFromTemplate } from '@/lib/api';
import { Link } from 'react-router-dom';
import { TemplateQuickFill } from '@/components/TemplateQuickFill';

export default function TemplatesPage() {
  const [featured, setFeatured] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TemplateItem | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await getBuiltinTemplates();
        if (mounted) setFeatured(res.templates);
      } catch (e: any) {
        setError(e?.message || 'Failed to load templates');
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginBottom: 8 }}>Templates</h1>
      <p style={{ marginTop: 0, color: '#666' }}>Featured Templates</p>
      {loading && <div>Loading…</div>}
      {error && <div style={{ color: 'crimson' }}>{error}</div>}
      {!loading && !error && (
        <div>
          <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 8 }}>
            {featured.map((tpl) => (
              <TemplateCard key={tpl.id} item={tpl} onClick={() => setSelected(tpl)} />
            ))}
          </div>
          <h2 style={{ marginTop: 24 }}>All Templates</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
            {featured.map((tpl) => (
              <TemplateCard key={tpl.id + '-grid'} item={tpl} onClick={() => setSelected(tpl)} />
            ))}
          </div>
        </div>
      )}

      {selected && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)' }} onClick={() => setSelected(null)}>
          <div style={{ background: '#fff', maxWidth: 640, margin: '10vh auto', padding: 24, borderRadius: 8 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>{selected.title}</h3>
              {selected.visibility === 'builtin' && (
                <span style={{ background: '#eef6ff', color: '#2563eb', padding: '2px 8px', borderRadius: 999, fontSize: 12 }}>Official</span>
              )}
            </div>
            <p style={{ color: '#444' }}>{selected.description}</p>
            {selected.visibility === 'builtin' ? (
              <BuiltinQuickFill templateId={selected.id} onClose={() => setSelected(null)} />
            ) : (
              <button
                style={{ marginTop: 12, padding: '10px 18px', fontSize: 16 }}
                onClick={async () => {
                  const res = await import('../lib/api').then(m => m.startRender({ template_id: selected.id, duration_sec: 10 }));
                  window.__track?.('render_start', { job_id: res.job_id });
                  window.location.href = `/render/${res.job_id}`;
                }}
              >
                Render with this template
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TemplateCard({ item, onClick }: { item: TemplateItem; onClick: () => void }) {
  return (
    <div role="button" onClick={onClick} style={{ cursor: 'pointer', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden', background: '#fff' }}>
      <div style={{ height: 120, background: '#f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
        {item.thumb ? (<img src={item.thumb} alt="thumb" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />) : (<span style={{ color: '#9ca3af' }}>No Preview</span>)}
        {item.visibility === 'builtin' && (
          <span style={{ position: 'absolute', top: 8, right: 8, background: '#eef6ff', color: '#2563eb', padding: '2px 8px', borderRadius: 999, fontSize: 12 }}>Official</span>
        )}
      </div>
      <div style={{ padding: 12 }}>
        <div style={{ fontWeight: 600 }}>{item.title}</div>
        <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>{item.description}</div>
        <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 8 }}>{item.category}</div>
      </div>
    </div>
  );
}

function BuiltinQuickFill({ templateId, onClose }: { templateId: string; onClose: () => void }) {
  const [vars, setVars] = useState<string[]>([]);
  const [schema, setSchema] = useState<any | undefined>(undefined);
  useEffect(() => {
    let mounted = true;
    // This page has been moved to _disabled to exclude it from the build.
    // Original functionality has been commented out.
    // useEffect(() => {
    //   let mounted = true;
    //   (async () => {
    //     try {
    //       const res = await getBuiltinTemplates();
    //       if (mounted) setFeatured(res.templates);
    //     } catch (e: any) {
    //       setError(e?.message || 'Failed to load templates');
    //     } finally {
    //       if (mounted) setLoading(false);
    //     }
    //   })();
    //   return () => { mounted = false; };
    // }, []);
    <div>
      <TemplateQuickFill
        vars={vars}
        schema={schema}
        onPreview={async (inputs) => {
          const r = await previewTemplatePlan(templateId, inputs);
          return { warnings: r.warnings };
        }}
        onRender={async (inputs) => {
          const r = await renderFromTemplate(templateId, { inputs });
          // navigate by hash link to keep modal dismissal
          window.location.hash = `#/render/${r.job_id}`;
          onClose();
        }}
      />
      <div style={{ marginTop: 12 }}>
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
