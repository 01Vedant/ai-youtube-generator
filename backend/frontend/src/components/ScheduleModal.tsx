/**
 * ScheduleModal: DateTime picker for scheduling YouTube publishing
 */

import React, { useState, useEffect } from 'react';
import { track } from '../lib/analytics';
import { fetchSchedule, schedulePublish, cancelScheduledPublish } from '../lib/api';
import { toast } from '../lib/toast';
import type { PublishSchedule } from '../types/api';
import './ScheduleModal.css';

export interface ScheduleModalProps {
  isOpen: boolean;
  jobId: string;
  title: string;
  onClose: () => void;
  onSchedule: (isoDatetime: string) => Promise<void>;
}

export const ScheduleModal: React.FC<ScheduleModalProps> = ({
  isOpen,
  jobId,
  title,
  onClose,
}) => {
  const [dateTime, setDateTime] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [schedule, setSchedule] = useState<PublishSchedule | null>(null);

  // Fetch current schedule status
  useEffect(() => {
    if (!isOpen) return;

    const loadSchedule = async () => {
      try {
        const data = await fetchSchedule(jobId);
        setSchedule(data);
        if (data && data.scheduled_at) {
          // Convert ISO to datetime-local format (remove Z and timezone)
          const localDateTime = data.scheduled_at.replace('Z', '').split('+')[0];
          setDateTime(localDateTime);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch schedule';
        console.error('Failed to fetch schedule:', message);
        // Non-blocking error for schedule fetch (may not exist yet)
      }
    };

    loadSchedule();
  }, [isOpen, jobId]);

  const handleSchedule = async () => {
    if (!dateTime) {
      setError('Please select a date and time');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Convert local datetime to ISO format
      const isoDatetime = new Date(dateTime).toISOString();
      await schedulePublish(jobId, isoDatetime);
      track('schedule_set', { job_id: jobId, datetime: isoDatetime });
      toast.success('Video scheduled successfully');
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to schedule';
      console.error('Failed to schedule publish:', err);
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleUnschedule = async () => {
    if (!schedule || schedule.state !== 'scheduled') return;

    setLoading(true);
    setError(null);

    try {
      await cancelScheduledPublish(jobId);

      track('schedule_cancelled', { job_id: jobId });
      toast.success('Schedule cancelled');
      setSchedule(null);
      setDateTime('');
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to cancel schedule';
      console.error('Failed to cancel schedule:', err);
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="schedule-modal-overlay" onClick={onClose} role="presentation">
      <div
        className="schedule-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="schedule-modal-title"
      >
        <header className="modal-header">
          <h2 id="schedule-modal-title">Schedule YouTube Publish</h2>
          <button
            className="close-btn"
            onClick={onClose}
            aria-label="Close schedule modal"
          >
            ✕
          </button>
        </header>

        <div className="modal-content">
          <p className="modal-subtitle">Video: {title}</p>

          {schedule && schedule.state === 'scheduled' && (
            <div className="alert alert-success">
              <strong>✓ Already scheduled:</strong>{' '}
              {new Date(schedule.scheduled_at || '').toLocaleString()}
            </div>
          )}

          {schedule?.error && (
            <div className="alert alert-warning">
              <strong>Previous schedule failed:</strong> {schedule.error}
            </div>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="schedule-datetime">
              Publish Date & Time
            </label>
            <input
              id="schedule-datetime"
              type="datetime-local"
              value={dateTime}
              onChange={(e) => setDateTime(e.target.value)}
              disabled={loading}
              aria-label="Select publish date and time"
              min={new Date().toISOString().slice(0, 16)}
            />
            <small className="form-hint">
              Select a future date and time. Times are converted to UTC for YouTube scheduling.
            </small>
          </div>
        </div>

        <footer className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onClose}
            disabled={loading}
            aria-label="Close without scheduling"
          >
            Cancel
          </button>

          {schedule && schedule.state === 'scheduled' && (
            <button
              className="btn btn-danger"
              onClick={handleUnschedule}
              disabled={loading}
              aria-label="Remove current schedule"
            >
              {loading ? '⏳ Unscheduling...' : '✕ Unschedule'}
            </button>
          )}

          <button
            className="btn btn-primary"
            onClick={handleSchedule}
            disabled={loading || !dateTime}
            aria-label="Confirm schedule"
          >
            {loading ? '⏳ Scheduling...' : '📅 Schedule Publish'}
          </button>
        </footer>
      </div>
    </div>
  );
};
