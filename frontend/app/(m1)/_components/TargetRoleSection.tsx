"use client";

// Target role (UP-13, REQ-F1-31 to F1-34): the student picks one role, and
// sees how many of its skills they need, already hold and still lack.
import { type FormEvent, useEffect, useId, useState } from "react";

import { api } from "@/lib/api";
import { errorMessage } from "@/lib/forms";
import type { Role, TargetRole } from "@/lib/types";

import { FormError } from "./FormMessages";

export function TargetRoleSection({ onUnauthorized }: { onUnauthorized: (status: number) => void }) {
  const selectId = useId();
  const [roles, setRoles] = useState<Role[]>([]);
  const [current, setCurrent] = useState<TargetRole | null>(null);
  const [choice, setChoice] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    api<Role[]>("/profile/roles").then(({ status, data }) => {
      if (status === 200) setRoles(data);
      else if (status === 401 || status === 403) onUnauthorized(status);
      else setError(errorMessage(data));
    });
    api<TargetRole>("/profile/target-role").then(({ status, data }) => {
      if (status === 200) {
        setCurrent(data);
        setChoice(String(data.role_id));
      } else if (status === 401 || status === 403) onUnauthorized(status);
      // 404 only means no role is chosen yet.
    });
  }, [onUnauthorized]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!choice) {
      setError("Choose a role first.");
      return;
    }
    setPending(true);
    const { status, data } = await api<TargetRole>("/profile/target-role", {
      method: "PUT",
      json: { role_id: Number(choice) },
    });
    setPending(false);
    if (status === 200) {
      setCurrent(data);
      setError("");
    } else if (status === 401 || status === 403) onUnauthorized(status);
    else setError(errorMessage(data));
  }

  return (
    <section aria-label="Target role">
      <h2>Target role</h2>
      <form onSubmit={save}>
        <label htmlFor={selectId}>Role</label>
        <select id={selectId} value={choice} onChange={(event) => setChoice(event.target.value)}>
          <option value="">Choose a role…</option>
          {roles.map((role) => (
            <option key={role.role_id} value={role.role_id}>
              {role.role_name}
            </option>
          ))}
        </select>
        <button type="submit" disabled={pending}>
          {pending ? "Saving…" : "Set target role"}
        </button>
      </form>
      <FormError message={error} />
      {current && (
        <p aria-label="Gap summary">
          {current.role_name}: {current.required} skills required, you hold {current.held}, gap{" "}
          {current.gap}.
        </p>
      )}
    </section>
  );
}
