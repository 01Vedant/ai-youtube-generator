// Moved to _disabled
import { useEffect, useMemo, useState } from 'react';
import { getMarketplaceTemplates, getMarketplaceTemplate, duplicateTemplate, previewTemplatePlan, renderFromTemplate } from '@/lib/api';
import type { TemplateItem } from '@/lib/api';
import { TemplateQuickFill } from '@/components/TemplateQuickFill';
import { useAuth } from '@/state/auth';
import { useNavigate, useLocation } from 'react-router-dom';
import { useFeatureFlags } from '@/hooks/useFeatureFlags';

export default function MarketplacePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { flags } = useFeatureFlags();
  const [items, setItems] = useState<TemplateItem[]>([]);
  const [total, setTotal] = useState(0);
  const sp = new URLSearchParams(location.search);
  const [q, setQ] = useState(sp.get('q') || '');
  const [category, setCategory] = useState<string>(sp.get('category') || '');
  const [sort, setSort] = useState<'new' | 'popular'>((sp.get('sort') as any) || 'new');
  const [page, setPage] = useState(Number(sp.get('page') || 1));
  const [pageSize, setPageSize] = useState(Number(sp.get('page_size') || 24));
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<TemplateItem | null>(null);
  const [vars, setVars] = useState<string[]>([]);
  const [schema, setSchema] = useState<any | undefined>(undefined);

  const pages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const usp = new URLSearchParams();
      if (q) usp.set('q', q);
      if (category) usp.set('category', category);
      if (sort) usp.set('sort', sort);
      usp.set('page', String(page));
      usp.set('page_size', String(pageSize));
      navigate({ pathname: '/marketplace', search: usp.toString() }, { replace: true });
      setLoading(true);
      try {
        const res = await getMarketplaceTemplates({ q, category: category || undefined, sort, page, page_size: pageSize });
        if (!mounted) return;
        setItems(res.items);
        setTotal(res.total);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [q, category, sort, page, pageSize]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!selected) return;
      try {
        const full = await getMarketplaceTemplate(selected.id);
        const schemaJson = full.inputs_schema;
        setSchema(schemaJson || undefined);
        // Detect vars client-side by scanning strings in plan_json (best-effort)
        const plan = full.plan_json as any;
        const tokens = new Set<string>();
        const VAR_RE = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g;
        const walk = (o: any) => {
          if (typeof o === 'string') {
            let m: RegExpExecArray | null;
            while ((m = VAR_RE.exec(o)) !== null) tokens.add(m[1]);
            return;
          }
          if (Array.isArray(o)) o.forEach(walk);
          else if (o && typeof o === 'object') Object.values(o).forEach(walk);
        };
        walk(plan);
        setVars(Array.from(tokens));
      } catch {
        setVars([]);
        setSchema(undefined);
      }
    })();
    return () => { mounted = false; };
  }, [selected]);

  return (
    <div style={{ padding: 24 }}>
      {flags && flags.marketplace === false ? (
        <div>
          <h1>Not Available</h1>
          <p>The marketplace is currently disabled.</p>
        </div>
      ) : (
        <>
      <h1>Template Marketplace</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search templates" />
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All Categories</option>
          <option value="story">Story</option>
          <option value="quotes">Quotes</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value as any)}>
          <option value="new">Newest</option>
          <option value="popular">Popular</option>
        </select>
      </div>
      {loading ? (
        <div>Loading…</div>
      ) : (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
            {items.map((tpl) => (
              <div key={tpl.id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
                <div style={{ height: 120, background: '#f3f4f6', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {tpl.thumb ? (<img src={tpl.thumb} alt="thumb" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />) : (<span style={{ color: '#9ca3af' }}>No Preview</span>)}
                  {tpl.visibility === 'builtin' && (
                    <span style={{ position: 'absolute', top: 8, right: 8, background: '#eef6ff', color: '#2563eb', padding: '2px 8px', borderRadius: 999, fontSize: 12 }}>Official</span>
                  )}
                  {tpl.visibility === 'shared' && (
                    <span style={{ position: 'absolute', top: 8, right: 8, background: '#ecfeff', color: '#155e75', padding: '2px 8px', borderRadius: 999, fontSize: 12 }}>Community</span>
                  )}
                </div>
                <div style={{ padding: 12 }}>
                  <div style={{ fontWeight: 600 }}>{tpl.title}</div>
                  <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>{tpl.description}</div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button onClick={() => setSelected(tpl)}>Preview</button>
                    <button onClick={async () => {
                      if (!user) {
                        // route to login preserving next
                        navigate(`/login?next=${encodeURIComponent('/marketplace' + (location.search || ''))}`);
                        return;
                      }
                      try {
                        const dup = await duplicateTemplate(tpl.id);
                        alert('Copied to your templates');
                        navigate('/templates');
                      } catch (e) {
                        alert('Duplicate failed');
                      }
                    }}>Duplicate</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12 }}>
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
            <span>Page {page} / {pages}</span>
            <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </div>
      )}

      {selected && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)' }} onClick={() => setSelected(null)}>
          <div style={{ background: '#fff', maxWidth: 640, margin: '10vh auto', padding: 24, borderRadius: 8 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>{selected.title}</h3>
              <button onClick={() => setSelected(null)}>Close</button>
            </div>
            <TemplateQuickFill
              vars={vars}
              schema={schema}
              onPreview={async (inputs) => {
                const r = await previewTemplatePlan(selected.id, inputs);
                return { warnings: r.warnings };
              }}
              onRender={async (inputs) => {
                if (!user) return; // hide render for unauthenticated
                const r = await renderFromTemplate(selected.id, { inputs });
                window.location.hash = `#/render/${r.job_id}`;
                setSelected(null);
              }}
            />
            {!user && (
              <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>Sign in to render or duplicate.</div>
            )}
          </div>
        </div>
      )}

      {!loading && items.length === 0 && (
        <div style={{ marginTop: 24, textAlign: 'center', color: '#6b7280' }}>
          No templates found. Try a different search.
          <div style={{ marginTop: 8 }}>
            <button onClick={() => { setQ(''); setCategory(''); setSort('new'); setPage(1); }}>Clear filters</button>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
}
