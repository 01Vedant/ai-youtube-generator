/**
 * AccountPage: GDPR export, delete account, rotate API key, backup status
 */

import React, { useEffect, useState } from 'react';
import './AccountPage.css';
import { toast } from '../lib/toast';
import { getAuthHeaders } from '../lib/api';

interface BackupStatus {
  last_backup: string;
  next_backup: string;
  backup_size_mb: number;
}

export const AccountPage: React.FC = () => {
  const [backupStatus, setBackupStatus] = useState<BackupStatus | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchBackupStatus();
  }, []);

  const fetchBackupStatus = async (): Promise<void> => {
    try {
      const response = await fetch('/api/account/backup-status', {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = (await response.json()) as BackupStatus;
        setBackupStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch backup status:', err);
    }
  };

  const handleExport = async (): Promise<void> => {
    setLoading(true);
    try {
      const response = await fetch('/api/account/export', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Export failed');

      const data = (await response.json()) as { download_url: string };
      if (data.download_url) {
        window.location.href = data.download_url;
        toast.success('Export ready! Download started.');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Export failed';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleRotateApiKey = async (): Promise<void> => {
    setLoading(true);
    try {
      const response = await fetch('/api/account/rotate-api-key', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to rotate API key');

      const data = (await response.json()) as { api_key: string };
      setApiKey(data.api_key);
      toast.success('API key rotated! Old key is now invalid.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to rotate API key';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async (): Promise<void> => {
    setLoading(true);
    try {
      const response = await fetch('/api/account/delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ confirm: true }),
      });
      if (!response.ok) throw new Error('Failed to delete account');

      toast.success('Account deletion initiated. You will be logged out shortly.');
      setTimeout(() => {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }, 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete account';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="account-page">
      <div className="container">
        <h1>⚙️ Account Settings</h1>

        {/* Data & Privacy */}
        <section className="account-section">
          <h2>📊 Data & Privacy (GDPR)</h2>
          <p>Export all your data or request permanent deletion.</p>

          <div className="action-card">
            <div className="action-info">
              <h3>📥 Export My Data</h3>
              <p>Download all your videos, scripts, and metadata as a ZIP file.</p>
              <small>Expires in 24 hours</small>
            </div>
            <button
              className="btn btn-secondary"
              onClick={handleExport}
              disabled={loading}
            >
              {loading ? '⏳ Exporting...' : 'Export Data'}
            </button>
          </div>

          <div className="action-card danger">
            <div className="action-info">
              <h3>🗑️ Delete My Account</h3>
              <p>Permanently delete your account and all associated data.</p>
              <small>This action cannot be undone</small>
            </div>
            {showDeleteConfirm ? (
              <div className="confirm-actions">
                <button className="btn btn-secondary" onClick={() => setShowDeleteConfirm(false)}>
                  Cancel
                </button>
                <button
                  className="btn btn-danger"
                  onClick={handleDeleteAccount}
                  disabled={loading}
                >
                  {loading ? '⏳ Deleting...' : 'Yes, Delete Everything'}
                </button>
              </div>
            ) : (
              <button
                className="btn btn-danger"
                onClick={() => setShowDeleteConfirm(true)}
              >
                Delete Account
              </button>
            )}
          </div>
        </section>

        {/* API & Integration */}
        <section className="account-section">
          <h2>🔑 API & Integration</h2>

          <div className="action-card">
            <div className="action-info">
              <h3>🔄 Rotate API Key</h3>
              <p>Generate a new API key and invalidate the old one.</p>
              <small>Use for security or credential leaks</small>
            </div>
            <button
              className="btn btn-secondary"
              onClick={handleRotateApiKey}
              disabled={loading}
            >
              {loading ? '⏳ Rotating...' : 'Rotate API Key'}
            </button>
          </div>

          {apiKey && (
            <div className="api-key-display">
              <label>New API Key</label>
              <div className="api-key-box">
                <code>{showApiKey ? apiKey : '••••••••••••••••••••'}</code>
                <button
                  className="btn-icon"
                  onClick={() => {
                    navigator.clipboard.writeText(apiKey);
                    toast.success('Copied to clipboard');
                  }}
                  title="Copy to clipboard"
                >
                  📋
                </button>
                <button
                  className="btn-icon"
                  onClick={() => setShowApiKey(!showApiKey)}
                  title="Toggle visibility"
                >
                  {showApiKey ? '🙈' : '👁️'}
                </button>
              </div>
              <small>Save this key in a secure location. You won't see it again.</small>
            </div>
          )}
        </section>

        {/* Backup & Recovery */}
        <section className="account-section">
          <h2>💾 Backup & Recovery</h2>

          {backupStatus && (
            <div className="backup-info">
              <div className="backup-row">
                <span>Last Backup:</span>
                <strong>{new Date(backupStatus.last_backup).toLocaleString()}</strong>
              </div>
              <div className="backup-row">
                <span>Next Backup:</span>
                <strong>{new Date(backupStatus.next_backup).toLocaleString()}</strong>
              </div>
              <div className="backup-row">
                <span>Backup Size:</span>
                <strong>{(backupStatus.backup_size_mb / 1024).toFixed(2)} GB</strong>
              </div>
            </div>
          )}

          <p className="backup-note">
            ✓ Your data is automatically backed up daily to encrypted offsite storage.
            All video projects, scripts, and metadata are included.
          </p>
        </section>

        {/* Session & Security */}
        <section className="account-section">
          <h2>🔐 Session & Security</h2>
          <div className="action-card">
            <div className="action-info">
              <h3>🚪 Sign Out</h3>
              <p>Sign out from this session and all other devices.</p>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => {
                localStorage.removeItem('access_token');
                window.location.href = '/login';
              }}
            >
              Sign Out
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};
