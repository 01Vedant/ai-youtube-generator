/**
 * TemplatesPanel: Quick-pick cards for preset Bhakti templates
 * Displayed in CreateVideoPage; on select, prefills form via /templates/plan
 */

import React, { useEffect, useState } from 'react';
import type { CreatorTemplate, RenderPlan } from '../types/api';
import { track } from '../lib/analytics';
import { getTemplates } from '../lib/api';
import './TemplatesPanel.css';

export interface TemplatesPanelProps {
  onSelectTemplate: (plan: RenderPlan) => void;
  language?: string;
  voice?: string;
}

export const TemplatesPanel: React.FC<TemplatesPanelProps> = ({
  onSelectTemplate,
  language = 'en',
  voice = 'F',
}) => {
  const [templates, setTemplates] = useState<CreatorTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchTemplates = async () => {
      setLoading(true);
      setError(null);
      try {
        const data: any = await getTemplates();
        setTemplates(data.templates || data || []);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load templates';
        setError(msg);
        console.error('TemplatesPanel fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTemplates();
  }, []);

  const handleSelectTemplate = async (templateId: string, title: string) => {
    setSelectedId(templateId);
    try {
      const res = await fetch('/api/templates/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          language,
          length_sec: 60,
          voice,
          style_ref: undefined,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const plan: RenderPlan = await res.json();

      track('schedule_opened', { template_id: templateId, title });
      onSelectTemplate(plan);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to build plan';
      console.error('Template plan builder error:', err);
      setError(msg);
    } finally {
      setSelectedId(null);
    }
  };

  if (loading) {
    return (
      <section className="templates-panel" role="region" aria-label="Video Templates">
        <h2>Quick Start with Templates</h2>
        <div className="templates-loading">Loading templates...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="templates-panel" role="region" aria-label="Video Templates">
        <h2>Quick Start with Templates</h2>
        <div className="templates-error">Failed to load templates: {error}</div>
      </section>
    );
  }

  if (templates.length === 0) {
    return (
      <section className="templates-panel" role="region" aria-label="Video Templates">
        <h2>Quick Start with Templates</h2>
        <div className="templates-empty">No templates available</div>
      </section>
    );
  }

  return (
    <section className="templates-panel" role="region" aria-label="Video Templates">
      <div className="templates-header">
        <h2>Quick Start with Templates</h2>
        <p className="templates-subtitle">Choose a preset to get started instantly</p>
      </div>

      <div className="templates-grid">
        {templates.map((template) => (
          <article
            key={template.id}
            className={`template-card ${selectedId === template.id ? 'loading' : ''}`}
            role="button"
            tabIndex={0}
            aria-pressed={selectedId === template.id}
            onClick={() => handleSelectTemplate(template.id, template.title)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                handleSelectTemplate(template.id, template.title);
              }
            }}
          >
            <div className="template-icon">📖</div>
            <h3>{template.title}</h3>
            <p className="template-description">{template.description}</p>

            {template.tags && template.tags.length > 0 && (
              <div className="template-tags">
                {template.tags.slice(0, 2).map((tag) => (
                  <span key={tag} className="tag">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            <div className="template-meta">
              <span className="meta-item">
                🕐 ~{template.default_length}s
              </span>
              <span className="meta-item">
                🌐 {template.default_language === 'hi' ? 'हिंदी' : 'English'}
              </span>
            </div>

            {selectedId === template.id && (
              <div className="template-loading-spinner">
                <div className="spinner"></div>
              </div>
            )}

            <button
              className="template-use-btn"
              disabled={selectedId === template.id}
              aria-label={`Use ${template.title} template`}
            >
              {selectedId === template.id ? 'Loading...' : 'Use Template'}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
};
