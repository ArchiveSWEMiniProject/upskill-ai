"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/forms";
import type { ProgressRecord } from "@/lib/progress";

export function CompleteResource({ progress, onCompleted }: {
  progress: ProgressRecord; onCompleted: (record: ProgressRecord) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function complete() {
    setBusy(true); setError("");
    const result = await api<ProgressRecord>(`/progress/${progress.progress_id}/complete`, {
      method: "POST", json: {},
    });
    if (result.status === 200) onCompleted(result.data);
    else setError(errorMessage(result.data));
    setBusy(false);
  }

  if (progress.status === "completed") return null;
  return <div>
    {error && <p role="alert">{error}</p>}
    <button type="button" disabled={busy} onClick={complete}>
      {busy ? "Recording completion…" : "Mark complete"}
    </button>
  </div>;
}
