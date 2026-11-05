"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/forms";
import type { ProgressRecord } from "@/lib/progress";
import { ProgressUpdate } from "./ProgressUpdate";

type Resource = { item_id: number; title: string; source_url: string };

export function ResourceProgress({ resourceId }: { resourceId: number }) {
  const [resource, setResource] = useState<Resource | null>(null);
  const [progress, setProgress] = useState<ProgressRecord | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setResource(null);
    setProgress(null);
    setError("");
    api<Resource>(`/catalogue/${resourceId}`).then(({ status, data }) => {
      if (!active) return;
      if (status === 200) setResource(data);
      else setError(status === 401 ? "Sign in to track this resource." : errorMessage(data));
      setLoading(false);
    });
    return () => { active = false; };
  }, [resourceId]);

  async function enrol() {
    setBusy(true);
    setError("");
    const { status, data } = await api<ProgressRecord>("/progress/enrol", {
      method: "POST", json: { resource_id: resourceId },
    });
    if (status === 201) setProgress(data);
    else setError(errorMessage(data));
    setBusy(false);
  }

  return (
    <section aria-label="Resource progress">
      {loading && <p>Loading resource…</p>}
      {error && <p role="alert">{error}</p>}
      {resource && <>
        <h1>{resource.title}</h1>
        <a href={resource.source_url} target="_blank" rel="noreferrer">Open learning resource</a>
        {!progress && <button type="button" disabled={busy} onClick={enrol}>
          {busy ? "Enrolling…" : "Enrol / resume tracking"}
        </button>}
        {progress && <p role="status">{progress.status}: {progress.completion_percentage}% complete</p>}
        {progress && <ProgressUpdate progress={progress} onUpdated={setProgress} />}
      </>}
    </section>
  );
}
