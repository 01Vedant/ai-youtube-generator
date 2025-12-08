import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getRender } from "../lib/api";

// minimal types to match backend responses
type JobStatus = "queued" | "pending" | "processing" | "done" | "error";
type Artifacts = { video?: string; audio?: string; thumbnail?: string } | null | undefined;

type RenderJob = {
  id: string;
  status: JobStatus;
  artifacts?: Artifacts;
  error?: string | null;
} | null;

type GetRenderResponse = {
  ok: boolean;
  data?: {
    id: string;
    status: JobStatus;
    artifacts?: Artifacts;
    error?: string | null;
  } | null;
  error?: string;
};

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Render Status</h1>
        <Link to="/" className="text-sm underline">Home</Link>
      </div>

      {!jobId && (
        <div className="rounded-lg border p-4">
          <p className="text-red-600">Missing jobId in URL.</p>
        </div>
      )}

      {jobId && (
        <div className="rounded-lg border p-4 space-y-3">
          <div>
            <div className="text-sm text-gray-500">Job ID</div>
            <div className="font-mono text-sm break-all">{jobId}</div>
          </div>

          <div>
            <div className="text-sm text-gray-500">Status</div>
            <div className="font-medium">{loading ? "loading…" : job?.status ?? "unknown"}</div>
          </div>

          {isError && <div className="text-red-600">{job?.error || "Render failed"}</div>}

          {isDone && (
            <div className="space-y-3">
              {a?.thumbnail && (
                <img src={a.thumbnail} alt="thumbnail" className="w-full rounded-lg border" />
              )}
              {a?.video && (
                <video src={a.video} controls className="w-full rounded-lg border" />
              )}
              {!a?.video && a?.audio && (
                <audio src={a.audio} controls className="w-full" />
              )}
            </div>
          )}

          {err && <div className="text-sm text-red-600">{err}</div>}
        </div>
      )}
    </div>
  );
}

import React from 'react';
import { useParams } from 'react-router-dom';

export default function RenderStatusPage() {
  const { jobId } = useParams();
  return (
    <div style={{ padding: 32 }}>
      <h1>Render Status</h1>
      <div>Job ID: {jobId}</div>
    </div>
  );
}
}
