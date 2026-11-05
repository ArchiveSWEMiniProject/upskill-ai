"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { errorMessage, fieldErrors } from "@/lib/forms";
import type { ProgressRecord } from "@/lib/progress";

export function ProgressUpdate({ progress, onUpdated }: {
  progress: ProgressRecord; onUpdated: (record: ProgressRecord) => void;
}) {
  const [value, setValue] = useState(String(progress.completion_percentage));
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setFieldError("");
    if (value.trim() === "") { setFieldError("Enter a completion percentage."); return; }
    setBusy(true);
    const result = await api<ProgressRecord>(`/progress/${progress.progress_id}`, {
      method: "PATCH", json: { completion_percentage: Number(value) },
    });
    if (result.status === 200) onUpdated(result.data);
    else {
      const detail = (result.data as unknown as { detail?: unknown })?.detail;
      setFieldError(fieldErrors(detail).completion_percentage ?? "");
      setError(errorMessage(result.data));
    }
    setBusy(false);
  }

  if (progress.status === "completed") return null;
  return <form onSubmit={save} noValidate aria-label="Update progress">
    <label htmlFor="completion-percentage">Completion percentage (0–100)</label>
    <input id="completion-percentage" type="number" min="0" max="100" step="1"
      value={value} onChange={e => setValue(e.target.value)} disabled={busy}
      aria-invalid={!!fieldError} aria-describedby={fieldError ? "percentage-error" : undefined} />
    {fieldError && <p id="percentage-error">{fieldError}</p>}
    {error && <p role="alert">{error}</p>}
    <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save progress"}</button>
  </form>;
}
