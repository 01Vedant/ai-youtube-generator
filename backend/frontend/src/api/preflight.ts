export type PreflightCheck = {
  name: string;
  status: "pass" | "warn" | "fail";
};

export type PreflightResponse = {
  ok: boolean;
  errors: string[];
  warnings: string[];
  checks: PreflightCheck[];
};

export async function runPreflight(): Promise<PreflightResponse> {
  const res = await fetch("/api/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Preflight failed: ${res.status} ${res.statusText} ${text}`);
  }

  return (await res.json()) as PreflightResponse;
}
