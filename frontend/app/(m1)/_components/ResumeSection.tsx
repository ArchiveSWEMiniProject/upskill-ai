"use client";

// Resume upload (UP-6, REQ-F1-08 to F1-11, F1-18). The API reads the file
// while the upload request is open, so the page shows the processing state:
// upload progress first, then "Processing your resume…" until the result.
import { type FormEvent, useEffect, useState } from "react";

import { api, uploadWithProgress } from "@/lib/api";
import { errorMessage } from "@/lib/forms";

import { FormError } from "./FormMessages";

// The API's limit and its exact message (REQ-F1-09). Checked here too so a
// 6 MB file is refused at once instead of after a long upload.
export const MAX_BYTES = 5 * 1024 * 1024;
export const SIZE_MESSAGE = "File exceeds the 5 MB limit.";
const ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export type Upload = {
  upload_id: number;
  file_name: string;
  file_type: "pdf" | "docx";
  size_bytes: number;
  status: "extracted" | "unreadable" | "failed";
  message: string | null;
  uploaded_at: string;
  delete_after: string;
  deleted: boolean;
};

type Phase = { kind: "idle" } | { kind: "uploading"; percent: number } | { kind: "processing" };

const STATUS_TEXT: Record<Upload["status"], string> = {
  extracted: "Read successfully",
  unreadable: "No readable text",
  failed: "Could not be processed",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// REQ-F1-18: say when the stored file goes, or that it already has.
export function retentionText(upload: Upload): string {
  return upload.deleted ? "File deleted" : `File deleted on ${formatDate(upload.delete_after)}`;
}

export function ResumeSection({ onUnauthorized }: { onUnauthorized: (status: number) => void }) {
  const [uploads, setUploads] = useState<Upload[] | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [done, setDone] = useState("");
  const [error, setError] = useState("");
  const busy = phase.kind !== "idle";

  useEffect(() => {
    api<Upload[]>("/profile/resume").then(({ status, data }) => {
      if (status === 200) setUploads(data);
      else if (status === 401 || status === 403) onUnauthorized(status);
      else setError(errorMessage(data));
    });
  }, [onUnauthorized]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = (form.elements.namedItem("file") as HTMLInputElement).files?.[0];
    setDone("");
    if (!file) return setError("Choose a PDF or DOCX file first.");
    if (file.size > MAX_BYTES) return setError(SIZE_MESSAGE);
    setError("");

    const body = new FormData();
    body.append("file", file);
    setPhase({ kind: "uploading", percent: 0 });
    const { status, data } = await uploadWithProgress<Upload>("/profile/resume", body, (percent) =>
      setPhase(percent === null ? { kind: "processing" } : { kind: "uploading", percent }),
    );
    setPhase({ kind: "idle" });

    if (status === 201) {
      form.reset();
      setUploads((current) => [data, ...(current ?? [])]);
      if (data.status === "extracted") setDone(`${data.file_name} was read successfully.`);
      else setError(data.message ?? STATUS_TEXT[data.status]);
    } else if (status === 401 || status === 403) {
      onUnauthorized(status);
    } else {
      setError(errorMessage(data));
    }
  }

  return (
    <section aria-labelledby="resume-title" aria-busy={busy}>
      <h2 id="resume-title">Resume</h2>
      <p className="hint">
        PDF or DOCX, up to 5 MB. Uploaded files are deleted 30 days after processing.
      </p>
      <form method="post" encType="multipart/form-data" noValidate onSubmit={onSubmit}
        aria-label="Upload a resume">
        <label>
          Resume file
          <input type="file" name="file" accept={ACCEPT} disabled={busy} />
        </label>
        <button type="submit" disabled={busy}>
          Upload resume
        </button>
      </form>
      <div role="status" className="progress">
        {phase.kind === "uploading" && (
          <>
            <progress max={100} value={phase.percent} aria-label="Upload progress" />
            <span>Uploading… {phase.percent}%</span>
          </>
        )}
        {phase.kind === "processing" && (
          <>
            <progress aria-label="Processing" />
            <span>Processing your resume…</span>
          </>
        )}
        {done && <span className="ok">{done}</span>}
      </div>
      <FormError message={error} />
      {uploads === null && !error && <p className="muted">Loading uploads…</p>}
      {Boolean(uploads?.length) && (
        <>
          <h3>Your uploads</h3>
          <ul className="entries" aria-label="Your uploads">
            {uploads!.map((upload) => (
              <li key={upload.upload_id}>
                <strong>{upload.file_name}</strong>
                <span className="muted">
                  {STATUS_TEXT[upload.status]} · uploaded {formatDate(upload.uploaded_at)} ·{" "}
                  {retentionText(upload)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
