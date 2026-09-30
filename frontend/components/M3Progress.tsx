"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Enrolment = {
  progress_id: number; resource_id: string; status: string; completion_percentage: number;
  score: number | null; recommendation_status: string; skill_update_status: string;
  evidence_status: string;
};
type Dashboard = {
  enrolments: Enrolment[]; completed_count: number; active_count: number;
  progress_percent: number; milestones: { milestone_id: number; kind: string }[];
  gaps_closed: number | null; gaps_status: string; streak_days: number | null; streak_status: string;
};

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function M3Progress() {
  const [studentId, setStudentId] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [resourceId, setResourceId] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const request = useCallback(async (path: string, init: RequestInit = {}) => {
    if (!studentId.trim()) throw new Error("Enter your student ID while M4 authentication is being integrated.");
    const headers = new Headers(init.headers);
    headers.set("X-Student-Id", studentId.trim());
    if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    const response = await fetch(`${api}${path}`, {
      ...init,
      headers,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail ?? "The request could not be completed.");
    return data;
  }, [studentId]);

  const refresh = useCallback(async () => {
    if (!studentId.trim()) return;
    try { setDashboard(await request("/dashboard/progress")); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to load progress."); }
  }, [request, studentId]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function act(event: FormEvent, operation: () => Promise<unknown>) {
    event.preventDefault(); setBusy(true); setMessage("");
    try { await operation(); await refresh(); setMessage("Progress saved."); }
    catch (error) { setMessage(error instanceof Error ? error.message : "The request could not be completed."); }
    finally { setBusy(false); }
  }

  return <section className="panel">
    <label className="field">Student ID <input value={studentId} onChange={e => setStudentId(e.target.value)} placeholder="M4 auth integration pending" /></label>
    <p className="notice">Temporary development identity field. Replace with the M4 authenticated session before deployment.</p>
    <form className="enrol" onSubmit={e => act(e, () => request("/progress/enrolments", { method: "POST", body: JSON.stringify({ resource_id: resourceId }) }))}>
      <label className="field">Learning resource ID <input value={resourceId} onChange={e => setResourceId(e.target.value)} required placeholder="Resource ID from the catalogue" /></label>
      <button disabled={busy}>Enrol</button>
    </form>
    {message && <p role="status" className="message">{message}</p>}
    {dashboard && <>
      <div className="summary" aria-label="Progress summary">
        <article><strong>{dashboard.active_count}</strong><span>Active</span></article>
        <article><strong>{dashboard.completed_count}</strong><span>Completed</span></article>
        <article><strong>{dashboard.progress_percent}%</strong><span>Average progress</span></article>
      </div>
      <h2>Your learning items</h2>
      {dashboard.enrolments.length === 0 ? <p>No enrolments yet.</p> : dashboard.enrolments.map(item => <article className="item" key={item.progress_id}>
        <div><h3>{item.resource_id}</h3>
          <p>{item.status} · {item.completion_percentage}% · Evidence: {item.evidence_status}</p>
          <p>Skill update: {item.skill_update_status} · Roadmap: {item.recommendation_status}</p>
        </div>
        {item.status !== "completed" && <div className="actions">
          <form onSubmit={e => act(e, () => request(`/progress/enrolments/${item.progress_id}`, { method: "PATCH", body: JSON.stringify({ completion_percentage: Number(new FormData(e.currentTarget).get("percentage")) }) }))}>
            <label>Progress % <input name="percentage" type="number" min="0" max="100" defaultValue={item.completion_percentage} required /></label><button disabled={busy}>Update</button>
          </form>
          <EvidenceForm busy={busy} onSubmit={(event, body) => act(event, () => request(
            `/progress/enrolments/${item.progress_id}/evidence${body instanceof FormData ? "/file" : ""}`,
            { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body) },
          ))} />
          <form onSubmit={e => void act(e, () => request(`/progress/enrolments/${item.progress_id}/complete`, { method: "POST" }))}>
            <button disabled={busy}>Complete</button>
          </form>
        </div>}
      </article>)}
      <h2>Milestones</h2>
      {dashboard.milestones.length ? <ul>{dashboard.milestones.map(m => <li key={m.milestone_id}>{m.kind}</li>)}</ul> : <p>No milestones recorded yet.</p>}
      <p className="notice">Skill gap closure: {dashboard.gaps_status}. Learning streaks: {dashboard.streak_status}.</p>
    </>}
  </section>;
}

function EvidenceForm({ busy, onSubmit }: { busy: boolean; onSubmit: (event: FormEvent, body: object | FormData) => Promise<void> }) {
  return <form onSubmit={e => {
    e.preventDefault();
    const form = e.currentTarget;
    const values = new FormData(form);
    const kind = String(values.get("type"));
    const file = values.get("file");
    const body = kind === "quiz"
      ? { evidence_type: "quiz", score: Number(values.get("score")) }
      : file instanceof File && file.size > 0
        ? (() => { const upload = new FormData(); upload.append("file", file); return upload; })()
        : { evidence_type: "certificate", evidence_url: String(values.get("url")) };
    void onSubmit(e, body).then(() => form.reset());
  }}>
    <label>Evidence <select name="type"><option value="certificate">Certificate link</option><option value="quiz">Quiz score</option></select></label>
    <input name="file" type="file" accept="application/pdf,.pdf" aria-label="Certificate PDF" />
    <input name="url" type="url" placeholder="Certificate URL" />
    <input name="score" type="number" min="0" max="100" placeholder="Quiz score" />
    <button disabled={busy}>Submit evidence</button>
  </form>;
}
