/**
 * Analytics: Simple event tracking for Creator Mode features
 */

// Typed event names for strict tracking
export type AnalyticsEventType =
  | "render_started"
  | "render_succeeded"
  | "render_failed"
  | "schedule_opened"
  | "schedule_set"
  | "schedule_cancelled"
  | "duplicate_clicked"
  | "library_opened";

export interface AnalyticsEvent {
  name: string;
  properties?: Record<string, unknown>;
  timestamp: string;
}

const events: AnalyticsEvent[] = [];

export function logEvent(name: string, properties?: Record<string, unknown>): void {
  const event: AnalyticsEvent = {
    name,
    properties,
    timestamp: new Date().toISOString(),
  };
  
  events.push(event);
  
  // Also log to console in development
  if (import.meta.env.DEV) {
    console.log(`[Analytics] ${name}`, properties);
  }
  
  // In production, send to analytics service (Amplitude, Mixpanel, etc.)
  // const endpoint = import.meta.env.VITE_ANALYTICS_ENDPOINT;
  // if (endpoint) {
  //   fetch(endpoint, { method: 'POST', body: JSON.stringify(event) }).catch(...);
  // }
}

/**
 * Track a typed analytics event with strict event names
 */
export function track(
  event: AnalyticsEventType,
  props?: Record<string, unknown>
): void {
  console.log("[analytics]", event, props ?? {});
  logEvent(event, props);
}

export function getEvents(): AnalyticsEvent[] {
  return [...events];
}

export function clearEvents(): void {
  events.length = 0;
}
