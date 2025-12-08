/**
 * UsageBanner: Show current month usage and % to quota
 * Displays on Create, Status, and Library pages
 */

import React, { useEffect, useState } from 'react';
import './UsageBanner.css';
import { getAuthHeaders } from '../lib/api';

interface UsageData {
  images_count: number;
  tts_seconds: number;
  render_minutes: number;
  storage_mb: number;
  uploads_count: number;
}

interface QuotaData {
  images_count: number;
  tts_seconds: number;
  render_minutes: number;
  storage_mb: number;
  uploads_count: number;
  plan: string;
}

export const UsageBanner: React.FC = () => {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [quota, setQuota] = useState<QuotaData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsage = async (): Promise<void> => {
      try {
        const response = await fetch('/api/usage', {
          headers: getAuthHeaders(),
        });
        if (response.ok) {
          const data = (await response.json()) as { usage: UsageData; quota: QuotaData };
          setUsage(data.usage);
          setQuota(data.quota);
        }
      } catch (err) {
        console.error('Failed to fetch usage:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchUsage();
  }, []);

  if (loading || !usage || !quota) {
    return null;
  }

  const renderPercent = (current: number, limit: number): number => {
    if (limit === 0 || limit === Infinity) return 0;
    return Math.round((current / limit) * 100);
  };

  const isNearLimit = (current: number, limit: number, threshold: number = 80): boolean => {
    return renderPercent(current, limit) >= threshold;
  };

  return (
    <div className="usage-banner">
      <div className="usage-header">
        <h3>📊 Monthly Usage ({quota.plan} Plan)</h3>
        <a href="/billing" className="upgrade-link">
          {quota.plan === 'free' ? 'Upgrade to Pro' : 'Manage Plan'}
        </a>
      </div>

      <div className="usage-grid">
        <div className="usage-item">
          <div className="usage-label">Images Generated</div>
          <div className="usage-bar">
            <div
              className={`usage-fill ${
                isNearLimit(usage.images_count, quota.images_count) ? 'near-limit' : ''
              }`}
              style={{
                width: `${Math.min(renderPercent(usage.images_count, quota.images_count), 100)}%`,
              }}
            ></div>
          </div>
          <div className="usage-stats">
            {usage.images_count} / {quota.images_count}
          </div>
        </div>

        <div className="usage-item">
          <div className="usage-label">TTS Seconds</div>
          <div className="usage-bar">
            <div
              className={`usage-fill ${
                isNearLimit(usage.tts_seconds, quota.tts_seconds) ? 'near-limit' : ''
              }`}
              style={{
                width: `${Math.min(renderPercent(usage.tts_seconds, quota.tts_seconds), 100)}%`,
              }}
            ></div>
          </div>
          <div className="usage-stats">
            {(usage.tts_seconds / 60).toFixed(0)}m / {(quota.tts_seconds / 60).toFixed(0)}m
          </div>
        </div>

        <div className="usage-item">
          <div className="usage-label">Render Minutes</div>
          <div className="usage-bar">
            <div
              className={`usage-fill ${
                isNearLimit(usage.render_minutes, quota.render_minutes) ? 'near-limit' : ''
              }`}
              style={{
                width: `${Math.min(renderPercent(usage.render_minutes, quota.render_minutes), 100)}%`,
              }}
            ></div>
          </div>
          <div className="usage-stats">
            {usage.render_minutes} / {quota.render_minutes}
          </div>
        </div>

        <div className="usage-item">
          <div className="usage-label">Storage (MB)</div>
          <div className="usage-bar">
            <div
              className={`usage-fill ${
                isNearLimit(usage.storage_mb, quota.storage_mb) ? 'near-limit' : ''
              }`}
              style={{
                width: `${Math.min(renderPercent(usage.storage_mb, quota.storage_mb), 100)}%`,
              }}
            ></div>
          </div>
          <div className="usage-stats">
            {(usage.storage_mb / 1024).toFixed(1)}GB / {(quota.storage_mb / 1024).toFixed(1)}GB
          </div>
        </div>
      </div>

      {Object.entries(usage).some(
        ([key, val]: [string, unknown]) => {
          const quotaKey = key as keyof QuotaData;
          return typeof val === 'number' && isNearLimit(val, quota[quotaKey] as number, 90);
        }
      ) && (
        <div className="usage-warning">
          ⚠️ You're approaching your usage limits. Upgrade to Pro for higher limits.
        </div>
      )}
    </div>
  );
};
