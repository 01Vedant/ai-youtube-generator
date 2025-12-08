import { useEffect, useState } from 'react';
import { submitFeedback } from '@/lib/api';
import { useLocation } from 'react-router-dom';

export default function FeedbackButton() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [category, setCategory] = useState<'bug'|'idea'|'confusion'>('confusion');
  const isLogin = location.pathname.startsWith('/login');
  if (isLogin) return null;

  const handleSubmit = async () => {
    if (!message.trim()) return;
    const parts = location.pathname.split('/').filter(Boolean);
    const job_id = parts[0] === 'render' && parts[1] ? parts[1] : undefined;
    const meta = {
      route: location.pathname,
      ua: navigator.userAgent,
      job_id,
      category,
    };
    await submitFeedback(message.trim(), meta);
    // Simple toast using alert; replace with project toast util if available
    // eslint-disable-next-line no-alert
    alert('Thanks! We got it.');
    setOpen(false); setMessage(''); setCategory('confusion');
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        style={{ position: 'fixed', right: 16, bottom: 16, borderRadius: 999, padding: '12px 16px', background: '#1f6feb', color: '#fff', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.15)', cursor: 'pointer', zIndex: 1000 }}
      >
        Feedback
      </button>
      {open && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1001 }}>
          <div style={{ background: '#fff', borderRadius: 8, width: 520, maxWidth: '90%', padding: 16 }}>
            <h3 style={{ margin: 0, marginBottom: 8 }}>Send Feedback</h3>
            <label style={{ display: 'block', fontSize: 12, color: '#555' }}>Message</label>
            <textarea value={message} onChange={e => setMessage(e.target.value)} rows={5} style={{ width: '100%', marginTop: 6, marginBottom: 12 }} required />
            <label style={{ display: 'block', fontSize: 12, color: '#555' }}>Category</label>
            <select value={category} onChange={e => setCategory(e.target.value as any)} style={{ width: '100%', marginTop: 6, marginBottom: 16 }}>
              <option value="bug">Bug</option>
              <option value="idea">Idea</option>
              <option value="confusion">Confusion</option>
            </select>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button onClick={() => setOpen(false)} style={{ padding: '8px 12px' }}>Cancel</button>
              <button onClick={handleSubmit} style={{ padding: '8px 12px', background: '#1f6feb', color: '#fff', border: 'none' }}>Submit</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}