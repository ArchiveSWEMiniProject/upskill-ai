"use client";

// Log in and register (UP-1). Registration creates a student account and logs
// straight in, so the student lands on their still-empty profile.
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { api, setToken } from "@/lib/api";
import { errorMessage, type FieldErrors, fieldErrors } from "@/lib/forms";

import { FieldError, FormError } from "./FormMessages";

const LOGIN_FAILED = "Invalid email or password";

async function logIn(email: string, password: string): Promise<string | null> {
  const { status, data } = await api("/auth/login", {
    method: "POST",
    json: { email, password },
  });
  if (status === 200) {
    setToken(data.access_token);
    return null;
  }
  return errorMessage(data, LOGIN_FAILED);
}

function credentials(event: FormEvent<HTMLFormElement>) {
  const form = new FormData(event.currentTarget);
  return { email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") };
}

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const { email, password } = credentials(event);
    setPending(true);
    const failure = await logIn(email, password);
    setPending(false);
    if (failure) setError(failure);
    else router.push("/profile");
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} aria-label="Log in">
      <label>
        Email
        <input name="email" type="email" autoComplete="username" required />
      </label>
      <label>
        Password
        <input name="password" type="password" autoComplete="current-password" required />
      </label>
      <FormError message={error} />
      <button type="submit" disabled={pending}>
        Log in
      </button>
    </form>
  );
}

export function RegisterForm() {
  const router = useRouter();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const { email, password } = credentials(event);
    setPending(true);
    const { status, data } = await api("/auth/register", {
      method: "POST",
      json: { email, password },
    });
    const failure = status === 201 ? await logIn(email, password) : null;
    setPending(false);
    setErrors(status === 422 ? fieldErrors(data?.detail) : {});
    if (status === 201 && !failure) router.push("/profile");
    else setError(status === 422 ? "" : (failure ?? errorMessage(data)));
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} aria-label="Create a student account">
      <label>
        Email
        <input
          name="email"
          type="email"
          autoComplete="email"
          required
          aria-invalid={Boolean(errors.email)}
          aria-describedby="register-email-error"
        />
        <FieldError id="register-email-error" message={errors.email} />
      </label>
      <label>
        Password
        <input
          name="password"
          type="password"
          autoComplete="new-password"
          required
          aria-invalid={Boolean(errors.password)}
          aria-describedby="register-password-hint register-password-error"
        />
        <span id="register-password-hint" className="hint">
          At least 8 characters, with a letter and a digit.
        </span>
        <FieldError id="register-password-error" message={errors.password} />
      </label>
      <FormError message={error} />
      <button type="submit" disabled={pending}>
        Create account
      </button>
    </form>
  );
}
