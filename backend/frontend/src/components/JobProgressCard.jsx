import React, { useEffect, useState } from 'react';
import { getJobStatus } from '../services/api';
import ScenePreview from './ScenePreview';

function ProgressBar({ value=0 }){
  return (
    <div className="w-full bg-white/10 rounded h-3">
      <div className="h-3 rounded bg-amber-400" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

export default function JobProgressCard({ job, setLastJob }){
  const [status, setStatus] = useState(job || null);
  const [polling, setPolling] = useState(true);

  useEffect(()=>{
    let mounted = true;
    async function fetchStatus(){
      try{
        const res = await getJobStatus(status.job_id);
        if(!mounted) return;
        setStatus(res);
        if(res && res.status === 'completed') setPolling(false);
      }catch(err){ console.warn('status poll failed', err); }
    }

    if(!status) return;
    fetchStatus();
    const id = setInterval(()=>{ if(polling) fetchStatus(); }, 3000);
    return ()=>{ mounted = false; clearInterval(id); };
  }, [status?.job_id, polling]);

  if(!status) return null;

  const scenes = status.scenes || [];
  const percent = status.progress_percent || (status.status === 'completed' ? 100 : 10);

  return (
    <div className="bg-white/5 border border-white/10 rounded p-4 mt-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Job: {status.job_id}</h3>
          <p className="text-sm text-white/70">Status: {status.status || 'queued'}</p>
        </div>
        <div className="w-64">
          <ProgressBar value={percent} />
          <div className="text-xs text-white/60 mt-1">{percent}%</div>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        { scenes.length === 0 && <div className="text-sm text-white/60">Waiting for scenes to be created…</div> }
        { scenes.map((s, idx) => (
          <div key={idx} className="p-2 bg-black/30 rounded">
            <div className="flex items-start gap-4">
              <div style={{ width: 160 }}><ScenePreview scene={s} /></div>
              <div className="flex-1">
                <div className="font-medium">{s.scene_title || `Scene ${idx+1}`}</div>
                <div className="text-sm text-white/60 mt-1">{s.notes || s.image_prompt || 'Image will appear here'}</div>
                <div className="text-xs text-white/50 mt-2">Duration: {s.duration || s.estimated_duration || '—'}s</div>
              </div>
            </div>
          </div>
        )) }
      </div>

      <div className="mt-4 flex gap-3">
        { status.project && status.project.final_video_url ? (
          <a className="px-4 py-2 bg-emerald-500 text-black rounded" href={status.project.final_video_url} target="_blank" rel="noreferrer">Download Final Video</a>
        ) : (
          <button className="px-4 py-2 bg-white/5 rounded" disabled>Final video not ready</button>
        ) }
        <button className="px-3 py-2 bg-white/5 rounded" onClick={()=>{ if(setLastJob) setLastJob(null); }}>Close</button>
      </div>
    </div>
  );
}
