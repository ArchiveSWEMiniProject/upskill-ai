"use client";

// Projects (UP-4, REQ-F1-03): add, edit and delete. The description shows a
// live character count against the 2000 limit (REQ-F1-37); an over-long
// description can still be submitted, and the API rejects it with its count.
import { type FormEvent, useId, useState } from "react";

import { countCharacters, counterLabel } from "@/lib/characters";
import type { FieldErrors } from "@/lib/forms";
import { type SaveResult, useEntries } from "@/lib/useEntries";

import { FieldError, FormError } from "./FormMessages";
import { TextField } from "./TextField";

export const DESCRIPTION_MAX = 2000;

export type Project = {
  project_id: number;
  title: string;
  description: string;
  repository_url: string | null;
};

type FormProps = {
  label: string;
  initial?: Project;
  submitLabel: string;
  onSubmit: (body: unknown) => Promise<SaveResult>;
  onDone?: () => void;
  onCancel?: () => void;
};

function ProjectForm({ label, initial, submitLabel, onSubmit, onDone, onCancel }: FormProps) {
  const id = useId();
  const [description, setDescription] = useState(initial?.description ?? "");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const count = countCharacters(description);

  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const url = String(values.get("repository_url") ?? "").trim();
    setPending(true);
    // The description is sent exactly as typed, so the API counts what the
    // student sees counted.
    const result = await onSubmit({
      title: String(values.get("title") ?? "").trim(),
      description,
      repository_url: url || null,
    });
    setPending(false);
    setErrors(result.ok ? {} : result.errors);
    setError(result.ok ? "" : result.message);
    if (result.ok) {
      if (!initial) {
        form.reset();
        setDescription("");
      }
      onDone?.();
    }
  }

  return (
    <form method="post" noValidate onSubmit={handle} aria-label={label}>
      <TextField label="Title" name="title" required maxLength={100}
        defaultValue={initial?.title} error={errors.title} />
      <label>
        Description
        <textarea
          name="description"
          required
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          aria-invalid={Boolean(errors.description)}
          aria-describedby={`${id}-count ${id}-error`}
        />
        <span id={`${id}-count`} className={count > DESCRIPTION_MAX ? "over-limit" : "hint"}>
          {counterLabel(count, DESCRIPTION_MAX)}
        </span>
        <FieldError id={`${id}-error`} message={errors.description} />
      </label>
      <TextField label="Repository URL" name="repository_url" type="url" maxLength={255}
        hint="Optional, an http:// or https:// address"
        defaultValue={initial?.repository_url ?? ""} error={errors.repository_url} />
      <FormError message={error} />
      <div className="row">
        <button type="submit" disabled={pending}>
          {submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

// Only http(s) links are rendered as links; the API accepts nothing else.
function RepositoryLink({ url }: { url: string | null }) {
  if (!url || !/^https?:\/\//i.test(url)) return null;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer">
      {url}
    </a>
  );
}

export function ProjectSection({ onUnauthorized }: { onUnauthorized: (status: number) => void }) {
  const { entries, error, save, remove } = useEntries<Project>(
    "/profile/projects",
    (project) => project.project_id,
    onUnauthorized,
  );
  const [editing, setEditing] = useState<number | null>(null);

  async function confirmDelete(project: Project) {
    if (window.confirm(`Delete the project "${project.title}"?`)) {
      await remove(project.project_id);
    }
  }

  return (
    <section aria-labelledby="projects-title">
      <h2 id="projects-title">Projects</h2>
      <FormError message={error} />
      {entries === null && !error && <p className="muted">Loading projects…</p>}
      {entries?.length === 0 && <p className="muted">No projects yet.</p>}
      {Boolean(entries?.length) && (
        <ul className="entries" aria-label="Your projects">
          {entries!.map((project) => (
            <li key={project.project_id}>
              {editing === project.project_id ? (
                <ProjectForm
                  label={`Edit ${project.title}`}
                  initial={project}
                  submitLabel="Save changes"
                  onSubmit={(body) => save(body, project.project_id)}
                  onDone={() => setEditing(null)}
                  onCancel={() => setEditing(null)}
                />
              ) : (
                <>
                  <strong>{project.title}</strong>
                  <span className="description">{project.description}</span>
                  <RepositoryLink url={project.repository_url} />
                  <div className="row">
                    <button type="button" className="secondary"
                      aria-label={`Edit ${project.title}`}
                      onClick={() => setEditing(project.project_id)}>
                      Edit
                    </button>
                    <button type="button" className="secondary"
                      aria-label={`Delete ${project.title}`}
                      onClick={() => confirmDelete(project)}>
                      Delete
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      <h3>Add a project</h3>
      <ProjectForm label="Add a project" submitLabel="Add project" onSubmit={(body) => save(body)} />
    </section>
  );
}
