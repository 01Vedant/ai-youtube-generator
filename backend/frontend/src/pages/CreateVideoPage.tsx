import { runPreflight, type PreflightResponse } from "../api/preflight";
import { PreflightStatusPill } from "@/components/PreflightStatusPill";
import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { startRender, ttsPreview, listProjects, assignToProject, sendOnboardingEvent } from '../lib/api';
import type { Project } from '@/types/projects';
import { toast } from '../lib/toast';
import type { RenderPlan, SceneInput } from '../types/api';
import { TemplatesPanel } from '../components/TemplatesPanel';
import './CreateVideoPage.css';
import { presets, presetToPlan } from '@/lib/presets';
import { getPrefs, savePrefs } from '@/lib/userPrefs';
import { UsageBadge } from '@/components/UsageBadge';

export const CreateVideoPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftShown, setDraftShown] = useState(false);
  const [fastPathPreview, setFastPathPreview] = useState(false);
  const [ttsPreviewUrls, setTtsPreviewUrls] = useState<Record<number, { url: string; duration_sec: number } | null>>({});
  const [previewLoading, setPreviewLoading] = useState<Record<number, boolean>>({});
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');

  // Preflight (backend readiness checks)
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [preflightError, setPreflightError] = useState<string | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);

  const onRunPreflight = async (): Promise<void> => {
    setPreflightLoading(true);
    setPreflightError(null);

    try {
      const res = await runPreflight();
      setPreflight(res);

      if (res.ok) toast.success("Preflight OK");
      else toast.error("Preflight found issues");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setPreflight(null);
      setPreflightError(msg);
      toast.error("Preflight failed");
    } finally {
      setPreflightLoading(false);
    }
  };

  const [formData, setFormData] = useState<RenderPlan>(() => {
    // Check if restoring from duplication
    const state = location.state as { prefill?: RenderPlan } | undefined;
    return (
      state?.prefill || {
        topic: 'Sanatan Dharma',
        language: 'en',
        voice: 'F',
        length: 30,
        style: 'cinematic',
        scenes: [
          {
            image_prompt: 'Ancient temple at sunrise, ultra-detailed',
            narration: 'Welcome to the teachings of Sanatan Dharma.',
            duration_sec: 3,
          },
        ],
        enable_parallax: true,
        enable_templates: true,
        enable_audio_sync: true,
        quality: 'final',
      }
    );
  });

  // Load prefs on mount and prefill defaults
  useEffect(() => {
    const prefs = getPrefs();
    setFormData((prev) => ({
      ...prev,
      voice_id: prefs.voice_id ?? prev.voice_id,
      style: prefs.template ?? prev.style,
      scenes: prev.scenes.map((s) => ({
        ...s,
        duration_sec: typeof s.duration_sec === 'number' ? s.duration_sec : (prefs.duration_default ?? 6),
      })),
    }));
  }, []);
  
  const handleResetToBlank = (): void => {
    setFormData({
      topic: '',
      language: 'en',
      voice: 'F',
      length: 30,
      style: 'cinematic',
      scenes: [{ image_prompt: '', narration: '', duration_sec: 3 }],
    });
    setFastPathPreview(false);
    setTtsPreviewUrls({});
    toast.info('Form reset to blank');
  };

  const handleLoadHindiSample = (): void => {
    setFormData({
      topic: 'Hindi TTS Sample',
      language: 'hi',
      voice: 'F',
      voice_id: 'hi-IN-SwaraNeural',
      length: 30,
      style: 'devotional',
      scenes: [
        {
          image_prompt: 'temple at sunrise, cinematic',
          narration: 'भोर की शांति…',
          duration_sec: 4,
        },
        {
          image_prompt: 'mountain in golden light',
          narration: 'आंतरिक स्थिरता…',
          duration_sec: 4,
        },
      ],
      enable_parallax: true,
      enable_templates: true,
      enable_audio_sync: true,
      quality: 'preview',
    });
    setTtsPreviewUrls({});
    setFastPathPreview(false);
    toast.info('Hindi sample loaded');
  };

  // Show draft restored toast on mount if coming from duplication
  useEffect(() => {
    const state = location.state as { prefill?: RenderPlan } | undefined;
    if (state?.prefill && !draftShown) {
      toast.info('Draft restored from previous project');
      setDraftShown(true);
    }
  }, [location.state, draftShown]);

  // Load user's projects for selector
  useEffect(() => {
    (async () => {
      try {
        const ps = await listProjects();
        setProjects(ps);
      } catch {
        setProjects([]);
      }
    })();
  }, []);

  const isValid = useMemo(() => {
    if (formData.scenes.length === 0 || formData.scenes.length > 20) return false;
    if (!formData.topic.trim() || formData.length < 10 || formData.length > 600) return false;
    return formData.scenes.every((s: SceneInput) => {
      const duration = typeof s.duration_sec === 'number' ? s.duration_sec : parseFloat(String(s.duration_sec));
      return (
        s.image_prompt.trim() &&
        s.narration.trim() &&
        !Number.isNaN(duration) &&
        duration >= 0.5 &&
        duration <= 600
      );
    });
  }, [formData]);

  const handleRemoveScene = (idx: number): void => {
    setFormData((prev: RenderPlan) => ({
      ...prev,
      scenes: prev.scenes.filter((_: SceneInput, i: number) => i !== idx),
    }));
  };

  const handleSceneChange = (
    idx: number,
    field: keyof SceneInput,
    value: string | number
  ): void => {
    setFormData((prev: RenderPlan) => {
      const newScenes = [...prev.scenes];
      newScenes[idx] = { ...newScenes[idx], [field]: value };
      return { ...prev, scenes: newScenes };
    });
  };

  const handleTtsPreview = async (sceneIdx: number): Promise<void> => {
    const scene = formData.scenes[sceneIdx];
    if (!scene?.narration?.trim()) {
      toast.error('Please enter narration text first');
      return;
    }

    setPreviewLoading((prev) => ({ ...prev, [sceneIdx]: true }));
    setTtsPreviewUrls((prev) => ({ ...prev, [sceneIdx]: null }));
    
    try {
      const result = await ttsPreview({
        text: scene.narration,
        lang: formData.language,
        voice_id: formData.voice_id,
        pace: 0.9,
      });
      
      setTtsPreviewUrls((prev) => ({ ...prev, [sceneIdx]: result }));
      
      if (result.cached) {
        toast.info('Preview loaded (cached)');
      } else {
        toast.success('Preview ready!');
      }
    } catch (err) {
      if ((err as any)?.code === 'QUOTA_EXCEEDED') {
        const q = (err as any).payload?.detail?.error;
        const limit = q?.limit;
        const metric = q?.metric === 'tts_sec' ? 'seconds/day' : '';
        const resetAt = q?.reset_at ? new Date(q.reset_at).toLocaleTimeString() : '';
        setError(`Daily quota exceeded. Limit: ${limit} ${metric}. Resets at ${resetAt}.`);
        toast.error('Daily quota exceeded');
      } else {
        const message = err instanceof Error ? err.message : 'Network error: preview failed';
        toast.error(message);
      }
      setTtsPreviewUrls((prev) => ({ ...prev, [sceneIdx]: null }));
    } finally {
      setPreviewLoading((prev) => ({ ...prev, [sceneIdx]: false }));
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (!isValid) {
        throw new Error('Form validation failed');
      }

      // Add fast-path preview options if enabled
      let planToSubmit = fastPathPreview
        ? { ...formData, fast_path: true, render_mode: 'PROXY' as const, target_res: '1080p' as const }
        : formData;
      
      // Ensure duration_sec is numeric (coerce strings to floats)
      planToSubmit = {
        ...planToSubmit,
        scenes: planToSubmit.scenes.map(s => {
          const duration = typeof s.duration_sec === 'string' ? parseFloat(s.duration_sec) : s.duration_sec;
          return {
            ...s,
            duration_sec: Number.isNaN(duration) ? 3.0 : duration
          };
        })
      };

      const response = await startRender({ script: planToSubmit.topic || planToSubmit.scenes[0]?.narration || '', duration_sec: 10 });
      if (selectedProjectId) {
        try { await assignToProject(selectedProjectId, response.job_id); } catch {}
      }
      sendOnboardingEvent('rendered_first_video').catch(() => {});
      toast.success(`Video job created! ID: ${response.job_id}`);
      window.__track?.('render_start', { job_id: response.job_id });
      navigate(`/render/${response.job_id}`);
    } catch (err) {
      if ((err as any)?.code === 'QUOTA_EXCEEDED') {
        const q = (err as any).payload?.detail?.error;
        const limit = q?.limit;
        const resetAt = q?.reset_at ? new Date(q.reset_at).toLocaleTimeString() : '';
        setError(`Daily quota exceeded. Limit: ${limit} renders/day. Resets at ${resetAt}.`);
        toast.error('Daily quota exceeded');
      } else {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        toast.error(message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-video-page" data-testid="create-story-modal">
      <div className="container">
        {/* Templates Panel */}
        <section className="templates-section">
          <div className="templates-header">
            <TemplatesPanel
              onSelectTemplate={(plan: RenderPlan) => {
                setFormData(plan);
                setTtsPreviewUrls({});
                toast.info(`Template loaded: ${plan.topic}`);
              }}
            />
            <div className="form-group" style={{ marginLeft: 12 }}>
              <label htmlFor="preset">Presets</label>
              <select id="preset" onChange={(e) => {
                const pid = e.target.value;
                const p = presets.find(x => x.id === pid);
                if (!p) return;
                const plan = presetToPlan(p, formData.topic || 'Bhakti Video');
                setFormData(plan);
                setTtsPreviewUrls({});
                toast.info(`Applied preset '${p.name}'`);
                savePrefs({ template: p.template, voice_id: p.voice_id });
              }}>
                <option value="">(None)</option>
                {presets.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <PreflightStatusPill />
              <UsageBadge />
              <a href="#/usage" className="text-xs" style={{ marginLeft: 8 }} aria-label="View usage">View usage →</a>
              <button
                type="button"
                onClick={handleLoadHindiSample}
                className="btn-secondary"
                aria-label="Load Hindi sample"
                style={{ fontSize: '13px' }}
              >
                🇮🇳 Use Hindi Sample
              </button>
              <button
                type="button"
                onClick={handleResetToBlank}
                className="btn-secondary"
                aria-label="Reset form to blank"
              >
                🔄 Reset to Blank
              </button>
            </div>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="form">
          {/* Basic Settings */}
          <section className="form-section">
            <h2>Video Settings</h2>
            <div className="form-group">
              <label htmlFor="project">Project</label>
              <select
                id="project"
                value={selectedProjectId}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedProjectId(e.target.value)}
                aria-label="Select project"
              >
                <option value="">(None)</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.title}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="topic">Topic</label>
              <input
                id="topic"
                data-testid="title-input"
                type="text"
                value={formData.topic}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData((prev: RenderPlan) => ({ ...prev, topic: e.target.value }))}
                placeholder="e.g., Sanatan Dharma Principles"
                aria-required="true"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="language">Language</label>
                <select
                  id="language"
                  value={formData.language}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                    const newLang = e.target.value as 'en' | 'hi';
                    setFormData((prev: RenderPlan) => ({
                      ...prev,
                      language: newLang,
                      voice_id: newLang === 'hi' ? 'hi-IN-SwaraNeural' : undefined,
                    }));
                    // Clear TTS previews when language changes
                    setTtsPreviewUrls({});
                  }}
                  aria-label="Select language"
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                </select>
                {formData.language === 'hi' && (
                  <p className="form-help" style={{ marginTop: '4px', fontSize: '12px', color: '#666' }}>
                    Hindi voices: Swara (soothing), Diya (soft). We auto-match scene timing.
                  </p>
                )}
              </div>

              {formData.language === 'hi' && (
                <div className="form-group">
                  <label htmlFor="voice_id">Hindi Voice</label>
                  <select
                    id="voice_id"
                    value={formData.voice_id || 'hi-IN-SwaraNeural'}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                      const v = e.target.value;
                      savePrefs({ voice_id: v });
                      setFormData((prev: RenderPlan) => ({ ...prev, voice_id: v }));
                    }}
                    aria-label="Select Hindi voice"
                  >
                    <option value="hi-IN-SwaraNeural">Swara (soothing female)</option>
                    <option value="hi-IN-DiyaNeural">Diya (soft female)</option>
                  </select>
                </div>
              )}

              {formData.language === 'en' && (
                <div className="form-group">
                  <label htmlFor="voice">Voice</label>
                  <select
                    id="voice"
                    value={formData.voice}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                      setFormData((prev: RenderPlan) => ({
                        ...prev,
                        voice: e.target.value as 'F' | 'M',
                      }))
                    }
                    aria-label="Select voice"
                  >
                    <option value="F">Female</option>
                    <option value="M">Male</option>
                  </select>
                </div>
              )}

              <div className="form-group">
                <label htmlFor="length">Length (seconds)</label>
                <input
                  id="length"
                  type="number"
                  min="10"
                  max="600"
                  value={formData.length}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setFormData((prev: RenderPlan) => ({
                      ...prev,
                      length: parseInt(e.target.value, 10),
                    }))
                  }
                  aria-label="Video length in seconds"
                />
              </div>

              <div className="form-group">
                <label htmlFor="style">Style</label>
                <input
                  id="style"
                  type="text"
                  data-testid="description-input"
                  value={formData.style}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                    const t = e.target.value;
                    savePrefs({ template: t });
                    setFormData((prev: RenderPlan) => ({ ...prev, style: t }));
                  }}
                  placeholder="cinematic, vibrant, etc."
                  aria-label="Video style"
                />
              </div>
            </div>
          </section>

          {/* Scenes */}
          <section className="form-section">
            <h2>
              Scenes <span aria-live="polite">({formData.scenes.length})</span>
            </h2>
            <div className="form-group" style={{ maxWidth: 220 }}>
              <label htmlFor="default-duration">Default scene duration</label>
              <input id="default-duration" type="number" min={4} max={12} defaultValue={getPrefs().duration_default ?? 6}
                onChange={(e) => { const val = Math.max(4, Math.min(12, parseInt(e.target.value, 10))); savePrefs({ duration_default: val }); }} />
            </div>
            {formData.scenes.map((scene: SceneInput, idx: number) => (
              <div key={`scene-${idx}`} className="scene-editor">
                <div className="scene-header">
                  <h3>Scene {idx + 1}</h3>
                  {formData.scenes.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        handleRemoveScene(idx);
                      }}
                      className="btn-remove"
                      aria-label={`Remove scene ${idx + 1}`}
                    >
                      ✕ Remove
                    </button>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor={`image_prompt-${idx}`}>Image Prompt</label>
                  <input
                    id={`image_prompt-${idx}`}
                    type="text"
                    value={scene.image_prompt}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                      handleSceneChange(idx, 'image_prompt', e.target.value);
                    }}
                    placeholder="Describe the image you want to generate..."
                    aria-required="true"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor={`narration-${idx}`}>Narration Text</label>
                  <textarea
                    id={`narration-${idx}`}
                    data-testid="fulltext-input"
                    value={scene.narration}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
                      handleSceneChange(idx, 'narration', e.target.value);
                    }}
                    placeholder="What should be narrated in this scene?"
                    rows={3}
                    aria-required="true"
                  />
                  {formData.language === 'hi' && (
                    <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <button
                        type="button"
                        onClick={() => handleTtsPreview(idx)}
                        disabled={previewLoading[idx] || !scene.narration.trim()}
                        className="btn-secondary"
                        style={{ fontSize: '13px', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        aria-label={`Preview TTS for scene ${idx + 1}`}
                      >
                        {previewLoading[idx] ? (
                          <>
                            <span className="spinner" style={{ width: '12px', height: '12px', border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />
                            Loading...
                          </>
                        ) : (
                          <>🔊 Preview TTS</>
                        )}
                      </button>
                      {ttsPreviewUrls[idx] && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <audio
                              controls
                              src={`http://127.0.0.1:8000${ttsPreviewUrls[idx]!.url}`}
                              style={{ flex: 1, maxWidth: '350px' }}
                              data-testid="thumbnail"
                              aria-label={`TTS preview for scene ${idx + 1}`}
                            />
                            <span style={{ fontSize: '13px', color: '#666', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                              {Math.floor(ttsPreviewUrls[idx]!.duration_sec / 60)}:{(ttsPreviewUrls[idx]!.duration_sec % 60).toFixed(0).padStart(2, '0')}
                            </span>
                          </div>
                          {Math.abs(ttsPreviewUrls[idx]!.duration_sec - scene.duration_sec) > scene.duration_sec * 0.05 && (
                            <small style={{ color: '#f59e0b', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }} role="status">
                              ⚠️ Final render will auto-pace to scene length.
                            </small>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor={`duration_sec-${idx}`}>Duration (seconds)</label>
                  <input
                    id={`duration_sec-${idx}`}
                    type="number"
                    min="1"
                    max="10"
                    value={scene.duration_sec}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                      handleSceneChange(idx, 'duration_sec', parseFloat(e.target.value));
                    }}
                    aria-required="true"
                  />
                </div>
              </div>
            ))}
          </section>

          {/* Fast Path Preview Toggle */}
          <section className="form-section">
            <div className="form-group">
              <label htmlFor="fast-path-toggle" className="checkbox-label">
                <input
                  id="fast-path-toggle"
                  type="checkbox"
                  checked={fastPathPreview}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFastPathPreview(e.target.checked)}
                  aria-label="Enable fast path preview mode"
                />
                <span>⚡ Preview in 1080p (Fast Path - PROXY mode)</span>
              </label>
              <p className="form-help">
                Renders faster using GPU acceleration with reduced quality settings for quick previews.
              </p>
            </div>
          </section>

          {/* Hybrid Pipeline Features */}
          <section className="form-section">
            <h2>✨ Hybrid Pipeline Features</h2>
            
            <div className="form-group">
              <label htmlFor="enable-parallax" className="checkbox-label">
                <input
                  id="enable-parallax"
                  type="checkbox"
                  checked={formData.enable_parallax ?? true}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setFormData((prev: RenderPlan) => ({ ...prev, enable_parallax: e.target.checked }))
                  }
                  aria-label="Enable 2.5D parallax motion"
                />
                <span>🎬 2.5D Parallax Motion</span>
              </label>
              <p className="form-help">
                Adds depth-based layered motion to static images for cinematic camera moves.
              </p>
            </div>

            <div className="form-group">
              <label htmlFor="enable-templates" className="checkbox-label">
                <input
                  id="enable-templates"
                  type="checkbox"
                  checked={formData.enable_templates ?? true}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setFormData((prev: RenderPlan) => ({ ...prev, enable_templates: e.target.checked }))
                  }
                  aria-label="Enable motion templates"
                />
                <span>📐 Motion Templates</span>
              </label>
              <p className="form-help">
                Applies title reveals, caption animations, and professional transitions.
              </p>
            </div>

            <div className="form-group">
              <label htmlFor="enable-audio-sync" className="checkbox-label">
                <input
                  id="enable-audio-sync"
                  type="checkbox"
                  checked={formData.enable_audio_sync ?? true}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setFormData((prev: RenderPlan) => ({ ...prev, enable_audio_sync: e.target.checked }))
                  }
                  aria-label="Enable audio-led editing"
                />
                <span>🎵 Audio-Led Editing</span>
              </label>
              <p className="form-help">
                Syncs cuts and transitions to music beats, ducks background music during voiceover.
              </p>
            </div>

            <div className="form-group">
              <label htmlFor="quality">Quality Profile</label>
              <select
                id="quality"
                value={formData.quality ?? 'final'}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                  setFormData((prev: RenderPlan) => ({
                    ...prev,
                    quality: e.target.value as 'preview' | 'final',
                  }))
                }
                aria-label="Select quality profile"
              >
                <option value="preview">Preview (720p, fast encode, cq=28)</option>
                <option value="final">Final (1080p+, full quality, cq=18-22)</option>
              </select>
              <p className="form-help">
                Preview mode renders faster for quick iterations. Final mode produces production-ready output.
              </p>
            </div>
          </section>

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {/* Preflight output */}
          {(preflightError || preflight) && (
            <div style={{ marginTop: 12, padding: 12, border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8 }}>
              {preflightError && (
                <div role="alert">❌ {preflightError}</div>
              )}

              {preflight && (
                <div>
                  <div style={{ marginBottom: 8 }}>
                    <strong>Preflight:</strong> {preflight.ok ? "✅ OK" : "❌ Issues found"}
                  </div>

                  {preflight.errors?.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <div><strong>Errors</strong></div>
                      <ul>
                        {preflight.errors.map((e, idx) => (
                          <li key={idx}>❌ {e}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {preflight.warnings?.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <div><strong>Warnings</strong></div>
                      <ul>
                        {preflight.warnings.map((w, idx) => (
                          <li key={idx}>⚠️ {w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <div><strong>Checks</strong></div>
                    <ul>
                      {preflight.checks?.map((c, idx) => (
                        <li key={idx}>
                          {c.status === "pass" ? "✅" : c.status === "warn" ? "⚠️" : "❌"} {c.name}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="form-actions" style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <button
              type="button"
              onClick={onRunPreflight}
              className="btn-secondary"
              disabled={preflightLoading}
              aria-label="Run preflight checks"
            >
              {preflightLoading ? "Running Preflight..." : "Run Preflight"}
            </button>

            <button
              type="submit"
              data-testid="submit-create"
              disabled={loading || !isValid}
              className="btn-primary"
              aria-label={loading ? 'Creating video...' : 'Create video'}
            >
              {loading ? 'Creating Video...' : 'Create Video'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
