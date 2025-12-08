import { useLocation } from "react-router-dom";

type MaintenancePayload = {
  reason?: string;
  retryAfterSec?: number;
  allowlistHint?: string;
};

export default function MaintenancePage() {
  const location = useLocation();
  const payload: MaintenancePayload | undefined = (location.state as any)?.payload;

  return (
    <div className="p-6 space-y-2">
      <h1 className="text-2xl font-semibold">Maintenance</h1>
      <p>Were doing a quick update. Please try again soon.</p>
      {payload?.reason && <p className="text-sm opacity-70">Reason: {payload.reason}</p>}
      {payload?.retryAfterSec != null && (
        <p className="text-sm opacity-70">Retry after ~{payload.retryAfterSec}s</p>
      )}
      {payload?.allowlistHint && <p className="text-sm opacity-70">{payload.allowlistHint}</p>}
    </div>
  );
}
