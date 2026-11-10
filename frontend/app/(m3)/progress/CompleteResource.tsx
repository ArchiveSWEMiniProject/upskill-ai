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
  const [evidenceType, setEvidenceType] = useState("");
  const [value, setValue] = useState("");
  const [evidenceSaved, setEvidenceSaved] = useState(false);
  const completed = progress.status === "completed";

  async function complete() {
    setBusy(true); setError("");
    const evidence = evidenceType === "quiz"
      ? { evidence_type: "quiz", score: Number(value) }
      : evidenceType === "certificate"
        ? { evidence_type: "certificate", evidence_url: value.trim() }
        : undefined;
    const result = await api<ProgressRecord>(`/progress/${progress.progress_id}/complete`, {
      method: "POST", json: evidence ? { evidence } : {},
    });
    if (result.status === 200) {
      if (evidence) setEvidenceSaved(true);
      onCompleted(result.data);
    }
    else setError(errorMessage(result.data));
    setBusy(false);
  }

  if (evidenceSaved) return <p>Completion evidence saved.</p>;
  return <form onSubmit={event => { event.preventDefault(); void complete(); }}>
    {error && <p role="alert">{error}</p>}
    <label>
      Completion evidence
      <select value={evidenceType} disabled={busy} onChange={event => {
        setEvidenceType(event.target.value);
        setValue("");
      }}>
        <option value="">Choose evidence type (optional)</option>
        <option value="certificate">Certificate link</option>
        <option value="quiz">Self-assessment quiz</option>
      </select>
    </label>
    {evidenceType === "certificate" && <label>
      Certificate URL
      <input type="url" required maxLength={255} value={value} disabled={busy}
        onChange={event => setValue(event.target.value)} />
    </label>}
    {evidenceType === "quiz" && <label>
      Quiz score (0–100)
      <input type="number" required min={0} max={100} step={1} value={value} disabled={busy}
        onChange={event => setValue(event.target.value)} />
    </label>}
    {(!completed || evidenceType) && <button type="submit" disabled={busy}>
      {busy ? "Saving…" : completed ? "Save evidence" : "Mark complete"}
    </button>}
  </form>;
}
