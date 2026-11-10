"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type ApiResult } from "@/lib/api";
import { errorMessage } from "@/lib/forms";
import type { ProgressRecord } from "@/lib/progress";

type Snapshot = Pick<ProgressRecord, "status" | "completion_percentage"> & { occurred_at: string };
type ResourceProgress = ProgressRecord & { title: string | null; history: Snapshot[] };
type Dashboard = {
  resources: ResourceProgress[];
  completed_count: number;
  current_streak_days: number;
  milestones: { label: string; achieved_at: string | null }[];
  gap_summary: { closed: number; total: number } | null;
  gap_closure_proportion: number | null;
};

function DisplayTime({ value }: { value: string }) {
  return <time dateTime={value}>{new Date(value).toLocaleString()}</time>;
}

export default function ProgressDashboardPage() {
  const [result, setResult] = useState<ApiResult<Dashboard> | null>(null);

  useEffect(() => {
    let active = true;
    api<Dashboard>("/progress/dashboard").then(response => {
      if (active) setResult(response);
    });
    return () => { active = false; };
  }, []);

  const dashboard = result?.status === 200 ? result.data : null;
  const summary = dashboard?.gap_summary;
  const proportion = dashboard?.gap_closure_proportion;
  return <main>
    <Link href="/profile">Your profile</Link>
    <h1>Your progress</h1>
    {!result && <p role="status">Loading progress…</p>}
    {result && !dashboard && <p role="alert">
      {result.status === 401 ? "Sign in to view your progress." : errorMessage(result.data)}
    </p>}
    {dashboard && <>
      <dl>
        <dt>Resources completed</dt>
        <dd>{dashboard.completed_count}</dd>
        <dt>Current streak (days)</dt>
        <dd>{dashboard.current_streak_days}</dd>
        <dt>Skill gaps closed</dt>
        <dd>{summary
          ? summary.total === 0
            ? "No gaps identified"
            : `${summary.closed} of ${summary.total}${proportion == null
              ? "" : ` (${Math.round(proportion * 100)}%)`}`
          : "Gap summary unavailable"}</dd>
      </dl>
      <section aria-labelledby="milestones">
        <h2 id="milestones">Milestones</h2>
        {dashboard.milestones.length === 0 ? <p>No milestones yet.</p> : <ul>
          {dashboard.milestones.map(milestone => <li key={milestone.label}>
            {milestone.label}
            {milestone.achieved_at && <> · <DisplayTime value={milestone.achieved_at} /></>}
          </li>)}
        </ul>}
      </section>
      <section aria-labelledby="enrolments">
        <h2 id="enrolments">Enrolled resources</h2>
        {dashboard.resources.length === 0 ? <p>No enrolments yet.</p> : <ul>
          {dashboard.resources.map(resource => <li key={resource.progress_id}>
            {resource.title
              ? <Link href={`/progress/${resource.resource_id}`}>{resource.title}</Link>
              : `Resource #${resource.resource_id} (unavailable)`}
            <p>{resource.status} · {resource.completion_percentage}% complete</p>
            {resource.history.length > 0 && <details>
              <summary>Progress history</summary>
              <ol>{resource.history.map((event, index) =>
                <li key={`${event.occurred_at}-${index}`}>
                  <DisplayTime value={event.occurred_at} /> · {event.status}
                  {" · "}{event.completion_percentage}%
                </li>)}
              </ol>
            </details>}
          </li>)}
        </ul>}
      </section>
    </>}
  </main>;
}
