import React from 'react';

type Props = {
  id: string;
  title?: string;
  description?: string;
  thumbnailUrl?: string;
};

export default function ArtifactCard({ id, title, description, thumbnailUrl }: Props) {
  const img = thumbnailUrl ?? `/artifacts/${id}/thumb.png`;
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <img src={img} alt={title ?? id} style={{ width: '100%', borderRadius: 6 }} />
      <div style={{ marginTop: 8 }}>
        <strong>{title ?? id}</strong>
        {description && <p style={{ marginTop: 4 }}>{description}</p>}
      </div>
    </div>
  );
}
import React from 'react';

type Props = {
  id: string;
  title?: string;
  description?: string;
  thumbnailUrl?: string;
};

export default function ArtifactCard({ id, title, description, thumbnailUrl }: Props) {
  const img = thumbnailUrl ?? `/artifacts/${id}/thumb.png`;
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <img src={img} alt={title ?? id} style={{ width: '100%', borderRadius: 6 }} />
      <div style={{ marginTop: 8 }}>
        <strong>{title ?? id}</strong>
        {description && <p style={{ marginTop: 4 }}>{description}</p>}
      </div>
    </div>
  );
}
import React from 'react';

type Props = {
  id: string;
  title?: string;
  description?: string;
  thumbnailUrl?: string;
};

export default function ArtifactCard({ id, title, description, thumbnailUrl }: Props) {
  const img = thumbnailUrl ?? `/artifacts/${id}/thumb.png`;
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <img src={img} alt={title ?? id} style={{ width: '100%', borderRadius: 6 }} />
      <div style={{ marginTop: 8 }}>
        <strong>{title ?? id}</strong>
        {description && <p style={{ marginTop: 4 }}>{description}</p>}
      </div>
    </div>
  );
}
import React from 'react';

type Props = {
  id: string;
  title?: string;
  description?: string;
  thumbnailUrl?: string;
};

export default function ArtifactCard({ id, title, description, thumbnailUrl }: Props) {
  const img = thumbnailUrl ?? `/artifacts/${id}/thumb.png`;
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <img src={img} alt={title ?? id} style={{ width: '100%', borderRadius: 6 }} />
      <div style={{ marginTop: 8 }}>
        <strong>{title ?? id}</strong>
        {description && <p style={{ marginTop: 4 }}>{description}</p>}
      </div>
    </div>
  );
}
import React from 'react';

type Props = {
  id: string;
  title?: string;
  description?: string;
  thumbnailUrl?: string;
};

export default function ArtifactCard({ id, title, description, thumbnailUrl }: Props) {
  const img = thumbnailUrl ?? `/artifacts/${id}/thumb.png`;
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <img src={img} alt={title ?? id} style={{ width: '100%', borderRadius: 6 }} />
      <div style={{ marginTop: 8 }}>
        <strong>{title ?? id}</strong>
        import React from 'react';

        type Props = {
          id: string;
          title: string;
          date?: string;
          thumbnailUrl?: string;
        };

        export default function ArtifactCard({ id, title, date, thumbnailUrl }: Props) {
          const img = thumbnailUrl ?? `/artifacts/${id}/thumb.png`;
          return (
            <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12, width: 240 }}>
              <img src={img} alt={title} style={{ width: '100%', borderRadius: 6 }} />
              <div style={{ marginTop: 8 }}>
                <strong>{title}</strong>
                {date && <div style={{ fontSize: 12, color: '#888' }}>{date}</div>}
              </div>
            </div>
          );
    });
  };

  const handleOpenRegenerate = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    setRegenOpen(true);
  };

  // Poll share progress when shareId present
  useEffect(() => {
    let timer: number | undefined;
    let mounted = true;
    async function tick() {
      if (!shareId) return;
      try {
        const p = await getShareProgress(shareId);
        if (!mounted) return;
        setProgress(p);
        if (p.unlocked) {
          try {
            await shareUnlock(shareId);
            toast.success('Bonus +1 render added');
          } catch {
            // ignore
          }
          setPolling(false);
        }
      } catch {
        // swallow network errors quietly
      }
    }
    if (shareId && polling) {
      tick();
      timer = window.setInterval(tick, 10000);
    }
    return () => { mounted = false; if (timer) window.clearInterval(timer); };
  }, [shareId, polling]);

  return (
    <article
      className="artifact-card border rounded-md shadow-sm p-3 bg-white hover:shadow-md transition cursor-pointer"
      onClick={onClick}
      aria-label={`Video: ${title}`}
      role="article"
    >
      <div className="artifact-thumb mb-3">
        {resolvedThumb ? (
          <img src={resolvedThumb} alt={title} className="w-full h-40 object-cover rounded" loading="lazy" />
        ) : (
          <div className="w-full h-40 bg-gray-100 rounded flex items-center justify-center text-3xl">📹</div>
        )}
      </div>
      <div className="artifact-content">
        <h3 className="text-sm font-semibold mb-1 truncate">{title}</h3>
        <p className="text-xs text-gray-600 mb-2">{formatDate(createdAt)}</p>
        <div className="badges flex flex-wrap gap-2 mb-3">
          {voice && <span className="badge badge-voice text-xs px-2 py-1 rounded bg-blue-50 text-blue-700">{voice}</span>}
          <span className="badge badge-duration text-xs px-2 py-1 rounded bg-green-50 text-green-700">{formatDuration(durationSec)}</span>
          {template && <span className="badge badge-template text-xs px-2 py-1 rounded bg-purple-50 text-purple-700">{template}</span>}
        </div>
        <div className="actions flex flex-wrap items-center gap-2">
          <a
            href={resolvedVideo}
            download
            className={`text-xs px-3 py-1 border rounded ${resolvedVideo ? '' : 'opacity-50 pointer-events-none'}`}
            onClick={(e) => {
              e.stopPropagation();
              // Soft-gate download if backend will serve S3-only links for Pro
              const isFree = (user?.plan_id ?? 'free') === 'free';
              const isS3 = resolvedVideo?.includes('amazonaws.com') || resolvedVideo?.includes('s3.') || resolvedVideo?.includes('presigned');
              if (isFree && isS3) {
                e.preventDefault();
                toast.error('Pro feature');
              }
            }}
            title={(user?.plan_id ?? 'free') === 'free' ? 'Pro feature' : undefined}
            aria-label="Download video"
          >
            Download
          </a>
          <button
            type="button"
            className="text-xs px-3 py-1 border rounded"
            onClick={handleCopyLink}
            aria-label="Copy video link"
          >
            Copy link
          </button>
          <button
            type="button"
            className="text-xs px-3 py-1 border rounded"
            onClick={handleShare}
            aria-label="Share video"
          >
            Share
          </button>
          <button
            type="button"
            className="text-xs px-3 py-1 border rounded"
            onClick={handleShareLink}
            aria-label="Share link"
          >
            Share link
          </button>
          <a
            href={resolvedVideo}
            target="_blank"
            rel="noopener"
            className="text-xs underline"
            onClick={(e) => e.stopPropagation()}
            aria-label="Open video in new tab"
          >
            Open
          </a>
          <button
            type="button"
            className="text-xs px-3 py-1 border rounded"
            onClick={handleExportYouTube}
            aria-label="Export to YouTube"
          >
            {user?.entitlements?.features?.includes('youtube_export') ? 'Export to YouTube' : 'Export (Pro)'}
          </button>
          {manifest && (
            <>
              <a
                href={manifest.thumbnail}
                target="_blank"
                rel="noopener"
                className="text-xs underline"
                onClick={(e) => e.stopPropagation()}
                aria-label="Open thumbnail"
              >
                Thumbnail
              </a>
              <a
                href={manifest.audio}
                target="_blank"
                rel="noopener"
                className="text-xs underline"
                onClick={(e) => e.stopPropagation()}
                aria-label="Open audio"
              >
                Audio
              </a>
            </>
          )}
          {canUseRegenerate(user?.plan_id ?? 'free') ? (
            <button
              type="button"
              className="text-xs px-3 py-1 border rounded"
              onClick={handleOpenRegenerate}
              aria-label="Regenerate"
            >
              Regenerate
            </button>
          ) : (
            <span className="text-xs px-3 py-1 border rounded" title="Pro feature">
              Regenerate (Pro)
            </span>
          )}
        </div>
      </div>
      {shareId && (
        <div className="mt-2 text-[11px] text-gray-700" aria-live="polite">
          {progress?.unlocked
            ? 'Share to unlock +1 render: Unlocked ✅'
            : `Share to unlock +1 render: ${progress?.unique_visitors ?? 0}/${progress?.goal ?? 3}`}
        </div>
      )}
      <RegenerateDialog
        open={regenOpen}
        onClose={() => setRegenOpen(false)}
        jobId={id}
        initial={{ title, voice, template, duration_sec: durationSec }}
        onQueued={(newJobId) => navigate(`/render/${newJobId}`)}
      />
    </article>
  );
};

export default ArtifactCard;