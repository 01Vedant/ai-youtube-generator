/**
 * ActivityLogPanel - Displays real-time activity log events for a render job
 * Polls every 3 seconds to fetch latest events
 */
import { useState, useEffect } from 'react';
import { getJobActivity } from '../lib/api';

interface Event {
  ts_iso: string;
  job_id: string;
  event_type: string;
  message: string;
  meta?: Record<string, unknown>;
}

interface ActivityLogPanelProps {
  jobId: string;
  limit?: number;
  pollInterval?: number;
}

export function ActivityLogPanel({
  jobId,
  limit = 100,
  pollInterval = 3000, // 3 seconds
}: ActivityLogPanelProps) {
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedMeta, setExpandedMeta] = useState<Set<number>>(new Set());

  useEffect(() => {
    const controller = new AbortController();
    let intervalId: number | undefined;

    const fetchEvents = async () => {
      try {
        const data = await getJobActivity(jobId, limit);
        setEvents(data.events);
        setError(null);
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message);
        }
      }
    };

    // Initial fetch
    fetchEvents();

    // Poll every pollInterval milliseconds
    intervalId = window.setInterval(fetchEvents, pollInterval);

    // Cleanup on unmount
    return () => {
      controller.abort();
      if (intervalId !== undefined) {
        clearInterval(intervalId);
      }
    };
  }, [jobId, limit, pollInterval]);

  const toggleMeta = (index: number) => {
    const newExpanded = new Set(expandedMeta);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedMeta(newExpanded);
  };

  const formatTime = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return isoString;
    }
  };

  const getEventTypeBadgeColor = (eventType: string): string => {
    if (eventType.includes('completed') || eventType.includes('success')) {
      return 'bg-green-100 text-green-800';
    }
    if (eventType.includes('started') || eventType.includes('created')) {
      return 'bg-blue-100 text-blue-800';
    }
    if (eventType.includes('failed') || eventType.includes('error')) {
      return 'bg-red-100 text-red-800';
    }
    return 'bg-gray-100 text-gray-800';
  };

  if (error) {
    return (
      <div className="activity-log-panel border border-red-200 rounded-lg p-4 bg-red-50">
        <h3 className="text-lg font-semibold text-red-800 mb-2">Activity Log</h3>
        <p className="text-red-600">Error loading activity: {error}</p>
      </div>
    );
  }

  return (
    <div className="activity-log-panel border border-gray-200 rounded-lg p-4 bg-white shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">Activity Log</h3>
      
      {events.length === 0 ? (
        <p className="text-gray-500 text-sm">No activity events yet...</p>
      ) : (
        <div className="space-y-2">
          {events.map((event, index) => (
            <div
              key={index}
              className="event-item border-l-2 border-gray-300 pl-3 py-1"
            >
              <div className="flex items-start gap-2">
                <span className="text-xs text-gray-500 font-mono whitespace-nowrap">
                  {formatTime(event.ts_iso)}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-medium ${getEventTypeBadgeColor(
                    event.event_type
                  )}`}
                >
                  {event.event_type}
                </span>
                <span className="text-sm text-gray-700 flex-1">
                  {event.message}
                </span>
                {event.meta && Object.keys(event.meta).length > 0 && (
                  <button
                    onClick={() => toggleMeta(index)}
                    className="text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    {expandedMeta.has(index) ? 'hide meta' : 'view meta'}
                  </button>
                )}
              </div>
              
              {event.meta && expandedMeta.has(index) && (
                <pre className="mt-2 text-xs bg-gray-50 border border-gray-200 rounded p-2 overflow-x-auto">
                  {JSON.stringify(event.meta, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
