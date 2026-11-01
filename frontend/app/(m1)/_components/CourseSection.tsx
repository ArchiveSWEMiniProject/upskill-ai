"use client";

// Completed courses (UP-3, REQ-F1-02): add, edit and delete. Missing fields and
// grades outside S-F / 0-100 are rejected by the API and shown under the field.
import { type FormEvent, useState } from "react";

import { type FieldErrors, formJson } from "@/lib/forms";
import { type SaveResult, useEntries } from "@/lib/useEntries";

import { FormError } from "./FormMessages";
import { TextField } from "./TextField";

export type Course = {
  course_id: number;
  course_name: string;
  course_code: string | null;
  grade: string;
  completion_term: string;
};

type FormProps = {
  label: string;
  initial?: Course;
  submitLabel: string;
  onSubmit: (body: unknown) => Promise<SaveResult>;
  onDone?: () => void;
  onCancel?: () => void;
};

function CourseForm({ label, initial, submitLabel, onSubmit, onDone, onCancel }: FormProps) {
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function handle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setPending(true);
    const result = await onSubmit(formJson(new FormData(form), ["course_code"]));
    setPending(false);
    setErrors(result.ok ? {} : result.errors);
    setError(result.ok ? "" : result.message);
    if (result.ok) {
      if (!initial) form.reset();
      onDone?.();
    }
  }

  return (
    <form method="post" noValidate onSubmit={handle} aria-label={label}>
      <TextField label="Course name" name="course_name" required maxLength={100}
        defaultValue={initial?.course_name} error={errors.course_name} />
      <TextField label="Course code" name="course_code" maxLength={15} hint="Optional"
        defaultValue={initial?.course_code ?? ""} error={errors.course_code} />
      <TextField label="Grade" name="grade" required maxLength={3}
        hint="S, A, B, C, D, E, F or a percentage from 0 to 100"
        defaultValue={initial?.grade} error={errors.grade} />
      <TextField label="Completion term" name="completion_term" required maxLength={10}
        hint="For example Sem 3" defaultValue={initial?.completion_term}
        error={errors.completion_term} />
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

function describe(course: Course): string {
  return [course.course_code, `Grade ${course.grade}`, course.completion_term]
    .filter(Boolean)
    .join(" · ");
}

export function CourseSection({ onUnauthorized }: { onUnauthorized: (status: number) => void }) {
  const { entries, error, save, remove } = useEntries<Course>(
    "/profile/courses",
    (course) => course.course_id,
    onUnauthorized,
  );
  const [editing, setEditing] = useState<number | null>(null);

  async function confirmDelete(course: Course) {
    if (window.confirm(`Delete the course "${course.course_name}"?`)) {
      await remove(course.course_id);
    }
  }

  return (
    <section aria-labelledby="courses-title">
      <h2 id="courses-title">Courses</h2>
      <FormError message={error} />
      {entries === null && !error && <p className="muted">Loading courses…</p>}
      {entries?.length === 0 && <p className="muted">No courses yet.</p>}
      {Boolean(entries?.length) && (
        <ul className="entries" aria-label="Your courses">
          {entries!.map((course) => (
            <li key={course.course_id}>
              {editing === course.course_id ? (
                <CourseForm
                  label={`Edit ${course.course_name}`}
                  initial={course}
                  submitLabel="Save changes"
                  onSubmit={(body) => save(body, course.course_id)}
                  onDone={() => setEditing(null)}
                  onCancel={() => setEditing(null)}
                />
              ) : (
                <>
                  <strong>{course.course_name}</strong>
                  <span className="muted">{describe(course)}</span>
                  <div className="row">
                    <button type="button" className="secondary"
                      aria-label={`Edit ${course.course_name}`}
                      onClick={() => setEditing(course.course_id)}>
                      Edit
                    </button>
                    <button type="button" className="secondary"
                      aria-label={`Delete ${course.course_name}`}
                      onClick={() => confirmDelete(course)}>
                      Delete
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      <h3>Add a course</h3>
      <CourseForm label="Add a course" submitLabel="Add course" onSubmit={(body) => save(body)} />
    </section>
  );
}
