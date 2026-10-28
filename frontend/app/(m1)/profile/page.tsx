"use client";

// The student's own profile (REQ-F1-39: there is no way to open anyone
// else's). Each part of the profile is its own section component and loads
// its own data once the profile exists.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, clearToken, getToken } from "@/lib/api";
import { errorMessage } from "@/lib/forms";
import type { Profile } from "@/lib/types";

import { CourseSection } from "../_components/CourseSection";
import { CreateProfileForm } from "../_components/CreateProfileForm";
import { FormError } from "../_components/FormMessages";
import { ProjectSection } from "../_components/ProjectSection";
import { ResumeSection } from "../_components/ResumeSection";

type State =
  | { kind: "loading" }
  | { kind: "missing" }
  | { kind: "ready"; profile: Profile }
  | { kind: "error"; message: string };

const STUDENTS_ONLY = "This page is for student accounts.";

export default function ProfilePage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "loading" });

  const logOut = useCallback(() => {
    clearToken();
    router.replace("/");
  }, [router]);

  // 401: the token is missing or expired, so start again from the login page.
  // 403: a faculty or administrator account opened the student page.
  const onUnauthorized = useCallback(
    (status: number) => {
      if (status === 401) logOut();
      else setState({ kind: "error", message: STUDENTS_ONLY });
    },
    [logOut],
  );

  useEffect(() => {
    if (!getToken()) {
      logOut();
      return;
    }
    api<Profile>("/profile").then(({ status, data }) => {
      if (status === 200) setState({ kind: "ready", profile: data });
      else if (status === 404) setState({ kind: "missing" });
      else if (status === 401 || status === 403) onUnauthorized(status);
      else setState({ kind: "error", message: errorMessage(data) });
    });
  }, [logOut, onUnauthorized]);

  return (
    <>
      <header>
        <h1>UpSkill-AI</h1>
        <button type="button" className="secondary" onClick={logOut}>
          Log out
        </button>
      </header>
      <main>
        {state.kind === "loading" && <p className="muted">Loading your profile…</p>}
        {state.kind === "error" && <FormError message={state.message} />}
        {state.kind === "missing" && (
          <CreateProfileForm
            onCreated={(profile) => setState({ kind: "ready", profile })}
            onUnauthorized={onUnauthorized}
          />
        )}
        {state.kind === "ready" && (
          <>
            <section aria-label="Profile">
              <h2>{state.profile.name}</h2>
              <p className="muted">
                {state.profile.education_level ?? "Education level not given"}
              </p>
            </section>
            <CourseSection onUnauthorized={onUnauthorized} />
            <ProjectSection onUnauthorized={onUnauthorized} />
            <ResumeSection onUnauthorized={onUnauthorized} />
          </>
        )}
      </main>
    </>
  );
}
