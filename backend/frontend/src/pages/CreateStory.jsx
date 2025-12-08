import React, { useState } from 'react';
import CreateStoryModal from '../components/CreateStoryModal';
import JobProgressCard from '../components/JobProgressCard';

export default function CreateStoryPage(){
  const [open, setOpen] = useState(true);
  const [lastJob, setLastJob] = useState(null);

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-900 via-purple-900 to-black text-white p-6">
      <div className="max-w-4xl mx-auto">
        <header className="mb-6">
          <h1 className="text-3xl font-semibold">Create Devotional Story</h1>
          <p className="text-indigo-200 mt-1">Convert a title or full story into a cinematic short — images, voiceover, and video.</p>
        </header>

        <main>
          <div className="mb-6">
            <button className="px-4 py-2 rounded bg-amber-500 text-black font-medium" onClick={()=>setOpen(true)}>New Story</button>
          </div>

          { lastJob && <JobProgressCard job={lastJob} setLastJob={setLastJob} /> }

          <CreateStoryModal open={open} onClose={()=>setOpen(false)} onSubmitted={(job)=>{ setLastJob(job); setOpen(false); }} />
        </main>
      </div>
    </div>
  );
}
