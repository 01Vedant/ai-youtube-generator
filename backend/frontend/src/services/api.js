// Simple API helpers for Create Story flow
const API_BASE = process.env.REACT_APP_API_BASE || '/api/v1';

// Placeholder mode: force use of placeholder assets even when real URLs available
// Useful for testing, development, and demo workflows
const PLACEHOLDER_MODE = process.env.REACT_APP_PLACEHOLDER_MODE === 'true';

async function jsonFetch(path, opts = {}){
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' , ...(opts.headers||{})},
    credentials: 'include',
    ...opts,
  });
  const text = await res.text();
  try { return JSON.parse(text); } catch(e){ return text; }
}

export async function createProjectFromTitle(payload){
  return jsonFetch('/projects/create_from_title', { method: 'POST', body: JSON.stringify(payload)});
}

export async function getJobStatus(job_id){
  return jsonFetch(`/jobs/${job_id}`, { method: 'GET' });
}

export function previewImageUrl(scene){
  // Force placeholder in placeholder mode
  if(PLACEHOLDER_MODE) {
    return '/static/placeholders/placeholder_4k.svg';
  }
  
  // Otherwise use real URL if available
  if(scene && scene.image_url) return scene.image_url;
  return '/static/placeholders/placeholder_4k.svg';
}

export function previewAudioUrl(scene){
  // Force placeholder in placeholder mode
  if(PLACEHOLDER_MODE) {
    return null; // UI will use embedded data-URI
  }
  
  // Otherwise use real URL if available
  if(scene && scene.audio_url) return scene.audio_url;
  return null; // UI will present an accessible silent placeholder when null
}

export function finalVideoUrl(project){
  if(project && project.final_video_url) return project.final_video_url;
  return null;
}

/**
 * Get current mode (for debugging)
 */
export function getCurrentMode(){
  return {
    placeholder_mode: PLACEHOLDER_MODE,
    api_base: API_BASE,
    env: process.env.NODE_ENV
  };
}

export default {
  createProjectFromTitle,
  getJobStatus,
  previewImageUrl,
  previewAudioUrl,
  finalVideoUrl,
  getCurrentMode,
};
