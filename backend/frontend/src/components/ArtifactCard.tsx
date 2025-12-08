import { useEffect } from 'react';

interface ArtifactCardProps {
  id: string;
  title?: string;
  thumbnailUrl?: string;
  videoUrl?: string;
  createdAt?: string;
  durationSec?: number;
  voice?: 'Swara' | 'Diya';
  template?: string;
  shareId?: string;
  onClick?: () => void;
}

const ArtifactCard: React.FC<ArtifactCardProps> = ({
  id,
  title,
  thumbnailUrl,
  videoUrl,
  createdAt,
  durationSec,
  voice,
  template,
  shareId,
  onClick,
}) => {
  useEffect(() => {
    let mounted = true;
    const tick = async () => {
      if (!mounted) return;
      // Simulated polling logic placeholder
    };
    tick();
    const timer = setInterval(tick, 5000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [shareId]);

  return (
    <article onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <div style={{ border: '1px solid #eee', padding: 12, borderRadius: 6, display: 'grid', gap: 6 }}>
        <h3 style={{ margin: 0 }}>{title ?? id}</h3>
        {thumbnailUrl && <img src={thumbnailUrl} alt="Thumbnail" style={{ width: '100%', borderRadius: 4 }} />}
        {videoUrl && (
          <video src={videoUrl} controls style={{ width: '100%', borderRadius: 4 }}>
            Your browser does not support the video tag.
          </video>
        )}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 12, color: '#4b5563' }}>
          {createdAt && <span>{new Date(createdAt).toLocaleString()}</span>}
          {typeof durationSec === 'number' && <span>{Math.round(durationSec)}s</span>}
          {voice && <span>{voice}</span>}
          {template && <span>{template}</span>}
        </div>
      </div>
    </article>
  );
};

export default ArtifactCard;
