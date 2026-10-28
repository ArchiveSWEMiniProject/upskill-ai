"use client";

// Shown once, right after registration: an account has no profile until the
// student creates it (UP-2, REQ-F1-01).
import { type FormEvent, useState } from "react";

import { api } from "@/lib/api";
import { errorMessage, type FieldErrors, fieldErrors, formJson } from "@/lib/forms";
import type { Profile } from "@/lib/types";

import { FieldError, FormError } from "./FormMessages";

type Props = { onCreated: (profile: Profile) => void; onUnauthorized: (status: number) => void };

export function CreateProfileForm({ onCreated, onUnauthorized }: Props) {
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = formJson(new FormData(event.currentTarget), ["education_level"]);
    setPending(true);
    const { status, data } = await api<Profile>("/profile", { method: "POST", json: body });
    setPending(false);
    if (status === 201) return onCreated(data);
    if (status === 401 || status === 403) return onUnauthorized(status);
    setErrors(status === 422 ? fieldErrors((data as any)?.detail) : {});
    setError(status === 422 ? "" : errorMessage(data));
  }

  return (
    <section>
      <h2>Create your profile</h2>
      <form method="post" noValidate onSubmit={onSubmit} aria-label="Create your profile">
        <label>
          Name
          <input
            name="name"
            maxLength={60}
            autoComplete="name"
            required
            aria-invalid={Boolean(errors.name)}
            aria-describedby="profile-name-error"
          />
          <FieldError id="profile-name-error" message={errors.name} />
        </label>
        <label>
          Education level <span className="hint">Optional, for example UG or PG</span>
          <input
            name="education_level"
            maxLength={30}
            aria-invalid={Boolean(errors.education_level)}
            aria-describedby="profile-education-error"
          />
          <FieldError id="profile-education-error" message={errors.education_level} />
        </label>
        <FormError message={error} />
        <button type="submit" disabled={pending}>
          Create profile
        </button>
      </form>
    </section>
  );
}
