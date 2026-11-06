"use client";

// Review skills found in a resume (UP-7, UP-8; REQ-F1-13 to F1-17). Nothing
// found in a resume is on the profile until the student confirms it here:
// each skill can be confirmed (at the suggested level or another one) or
// rejected, and every skill at or above the high-confidence threshold can be
// confirmed in one action.
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { errorMessage } from "@/lib/forms";

import { FormError } from "./FormMessages";

const LEVELS = ["beginner", "intermediate", "advanced"] as const;
type Level = (typeof LEVELS)[number];

export type ExtractedSkill = {
  candidate_id: number;
  upload_id: number;
  skill_id: number;
  skill_name: string;
  suggested_level: Level;
  confidence: number;
  source_sentence: string;
  status: "pending" | "confirmed" | "rejected";
};

type Listing = { threshold: number; candidates: ExtractedSkill[] };
type Decision = { skill_name: string; status: "confirmed" | "rejected"; level: Level | null };

export const percent = (value: number) => `${Math.round(value * 100)}%`;

type Props = {
  // Changes whenever a resume is uploaded, so the list is fetched again.
  refreshKey: number;
  onUnauthorized: (status: number) => void;
};

export function ExtractedSkillsSection({ refreshKey, onUnauthorized }: Props) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [levels, setLevels] = useState<Record<number, Level>>({});
  const [done, setDone] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    const { status, data } = await api<Listing>("/profile/resume/extracted");
    if (status === 200) setListing(data);
    else if (status === 401 || status === 403) onUnauthorized(status);
    else if (status !== 404) setError(errorMessage(data));
  }, [onUnauthorized]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  async function send(path: string, json?: unknown) {
    setPending(true);
    setDone("");
    const { status, data } = await api(path, { method: "POST", json });
    setPending(false);
    if (status === 401 || status === 403) return onUnauthorized(status);
    if (status !== 200) return setError(errorMessage(data));
    setError("");
    const decisions: Decision[] = Array.isArray(data) ? data : data.confirmed;
    setDone(summary(decisions));
    await load();
  }

  function decide(skill: ExtractedSkill, action: "confirm" | "reject") {
    const level = levels[skill.candidate_id];
    const decision =
      action === "confirm" && level && level !== skill.suggested_level
        ? { candidate_id: skill.candidate_id, action, level }
        : { candidate_id: skill.candidate_id, action };
    return send("/profile/skills/confirm", { decisions: [decision] });
  }

  const candidates = listing?.candidates ?? [];
  const high = listing ? candidates.filter((c) => c.confidence >= listing.threshold) : [];

  if (!listing || (candidates.length === 0 && !done && !error)) return null;

  return (
    <section aria-labelledby="extracted-title">
      <h2 id="extracted-title">Skills found in your resume</h2>
      <p className="hint">
        None of these is on your profile until you confirm it. Check each one against the sentence
        it was found in.
      </p>
      {high.length > 0 && (
        <button type="button" disabled={pending}
          onClick={() => send("/profile/skills/confirm-high-confidence")}>
          Confirm all {high.length} at {percent(listing.threshold)} confidence or more
        </button>
      )}
      <div role="status">{done && <span className="ok">{done}</span>}</div>
      <FormError message={error} />
      {candidates.length > 0 && (
        <ul className="entries" aria-label="Skills to review">
          {candidates.map((skill) => (
            <li key={skill.candidate_id}>
              <strong>{skill.skill_name}</strong>
              <span className="muted">{percent(skill.confidence)} confidence</span>
              <blockquote>{skill.source_sentence}</blockquote>
              <label>
                Level for {skill.skill_name}
                <select
                  value={levels[skill.candidate_id] ?? skill.suggested_level}
                  onChange={(event) =>
                    setLevels({ ...levels, [skill.candidate_id]: event.target.value as Level })
                  }
                >
                  {LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" disabled={pending} onClick={() => decide(skill, "confirm")}
                aria-label={`Confirm ${skill.skill_name}`}>
                Confirm
              </button>
              <button type="button" className="secondary" disabled={pending}
                onClick={() => decide(skill, "reject")} aria-label={`Reject ${skill.skill_name}`}>
                Reject
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function summary(decisions: Decision[]): string {
  const confirmed = decisions.filter((d) => d.status === "confirmed").map((d) => d.skill_name);
  const rejected = decisions.filter((d) => d.status === "rejected").map((d) => d.skill_name);
  const parts = [];
  if (confirmed.length) parts.push(`Added to your profile: ${confirmed.join(", ")}.`);
  if (rejected.length) parts.push(`Rejected: ${rejected.join(", ")}.`);
  return parts.join(" ") || "Nothing to confirm.";
}
