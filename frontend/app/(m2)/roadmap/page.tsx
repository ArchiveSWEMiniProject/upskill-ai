"use client";

// The student's skill gap against their target role (RM-3, REQ-F2-04). The API
// returns the gap already ranked, so this page only shows it.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, clearToken, getToken } from "@/lib/api";
import { errorMessage } from "@/lib/forms";

import { type Gap, GapList } from "../_components/GapList";

type State =
  | { kind: "loading" }
  | { kind: "ready"; gap: Gap }
  | { kind: "no-profile" }
  | { kind: "no-role" }
  | { kind: "error"; message: string };

const STUDENTS_ONLY = "This page is for student accounts.";

export default function RoadmapPage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "loading" });

  const logOut = useCallback(() => {
    clearToken();
    router.replace("/");
  }, [router]);

  useEffect(() => {
    if (!getToken()) {
      logOut();
      return;
    }
    api<Gap>("/roadmap").then(({ status, data }) => {
      if (status === 200) setState({ kind: "ready", gap: data });
      else if (status === 404) setState({ kind: "no-profile" });
      else if (status === 409) setState({ kind: "no-role" });
      else if (status === 401) logOut();
      else if (status === 403) setState({ kind: "error", message: STUDENTS_ONLY });
      else setState({ kind: "error", message: errorMessage(data) });
    });
  }, [logOut]);

  return (
    <>
      <header>
        <h1>UpSkill-AI</h1>
        <div className="row">
          <a href="/profile">Profile</a>
          <button type="button" className="secondary" onClick={logOut}>
            Log out
          </button>
        </div>
      </header>
      <main>
        <section aria-labelledby="gap-title">
          <h2 id="gap-title">Your skill gap</h2>
          {state.kind === "loading" && <p className="muted">Loading your skill gap...</p>}
          {state.kind === "error" && (
            <p className="form-error" role="alert">
              {state.message}
            </p>
          )}
          {state.kind === "no-profile" && (
            <p>
              Create your profile first. <a href="/profile">Go to your profile</a>
            </p>
          )}
          {state.kind === "no-role" && <p>Choose a target role to see your skill gap.</p>}
          {state.kind === "ready" && (
            <>
              <p className="muted">Target role: {state.gap.role_name}</p>
              {state.gap.items.length === 0 ? (
                <p>You already meet every requirement for {state.gap.role_name}.</p>
              ) : (
                <GapList items={state.gap.items} />
              )}
            </>
          )}
        </section>
      </main>
    </>
  );
}
