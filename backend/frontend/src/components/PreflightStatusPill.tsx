import React, { useEffect, useMemo, useState } from "react";
import { runPreflight, type PreflightResponse } from "../api/preflight";

type Status = "idle" | "loading" | "pass" | "warn" | "fail";

const STORAGE_KEY = "bhaktigen:preflight:v1";
const MAX_AGE_MS = 10 * 60 * 1000; // 10 minutes

function safeJsonParse<T>(s: string | null): T | null {
  if (!s) return null;
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

export const PreflightStatusPill: React.FC = () => {
  const [status, setStatus] = useState<Status>("idle");
  const [data, setData] = useState<PreflightResponse | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const computed: Status = useMemo(() => {
    if (status === "loading") return "loading";
    if (!data) return status;
    if (!data.ok || data.errors.length > 0) return "fail";
    if (data.warnings.length > 0 || data.checks.some((c) => c.status === "warn")) return "warn";
    return "pass";
  }, [status, data]);

  const label = useMemo(() => {
    if (computed === "loading") return "Preflight…";
    if (computed === "pass") return "Ready";
    if (computed === "warn") return "Warnings";
    if (computed === "fail") return "Errors";
    return "Preflight";
  }, [computed]);

  const bg = useMemo(() => {
    if (computed === "pass") return "rgba(34,197,94,0.15)";
    if (computed === "warn") return "rgba(245,158,11,0.18)";
    if (computed === "fail") return "rgba(239,68,68,0.15)";
    return "rgba(148,163,184,0.18)";
  }, [computed]);

  const border = useMemo(() => {
    if (computed === "pass") return "rgba(34,197,94,0.45)";
    if (computed === "warn") return "rgba(245,158,11,0.50)";
    if (computed === "fail") return "rgba(239,68,68,0.45)";
    return "rgba(148,163,184,0.35)";
  }, [computed]);

  const details = useMemo(() => {
    if (errMsg) return errMsg;
    if (!data) return "Runs quick checks: ffmpeg + output folder writable";
    const e = data.errors.length ? `Errors: ${data.errors.length}` : "Errors: 0";
    const w = data.warnings.length ? `Warnings: ${data.warnings.length}` : "Warnings: 0";
    const firstWarn = data.warnings[0] ? ` • ${data.warnings[0]}` : "";
    const firstErr = data.errors[0] ? ` • ${data.errors[0]}` : "";
    return `${e}, ${w}${firstErr || firstWarn}`;
  }, [data, errMsg]);

  async function run(force: boolean): Promise<void> {
    setErrMsg(null);
    setStatus("loading");
    try {
      const res = await runPreflight();
      setData(res);
      setStatus("idle");
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ ts: Date.now(), data: res })
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Preflight failed";
      setErrMsg(msg);
      setData(null);
      setStatus("fail");
      if (force) sessionStorage.removeItem(STORAGE_KEY);
    }
  }

  // auto-run once per session (or use cached result if recent)
  useEffect(() => {
    const cached = safeJsonParse<{ ts: number; data: PreflightResponse }>(
      sessionStorage.getItem(STORAGE_KEY)
    );

    if (cached && Date.now() - cached.ts < MAX_AGE_MS) {
      setData(cached.data);
      setStatus("idle");
      return;
    }

    run(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div
        title={details}
        aria-label="Preflight status"
        style={{
          fontSize: 12,
          padding: "6px 10px",
          borderRadius: 999,
          border: `1px solid ${border}`,
          background: bg,
          userSelect: "none",
          whiteSpace: "nowrap",
        }}
      >
        {computed === "pass" ? "✅" : computed === "warn" ? "⚠️" : computed === "fail" ? "❌" : "🧪"}{" "}
        {label}
      </div>

      <button
        type="button"
        onClick={() => run(true)}
        style={{
          fontSize: 12,
          padding: "6px 10px",
          borderRadius: 10,
          border: "1px solid rgba(148,163,184,0.35)",
          background: "transparent",
          cursor: "pointer",
          whiteSpace: "nowrap",
        }}
        aria-label="Re-run preflight"
        disabled={computed === "loading"}
        title="Re-run preflight checks"
      >
        ↻ Re-run
      </button>
    </div>
  );
};
