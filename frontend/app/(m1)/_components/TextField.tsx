import { type InputHTMLAttributes, type ReactNode, useId } from "react";

import { FieldError } from "./FormMessages";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  name: string;
  error?: string;
  hint?: ReactNode;
};

// A labelled input with an optional hint, and its error underneath.
export function TextField({ label, name, error, hint, ...input }: Props) {
  const id = useId();
  const described = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ");
  return (
    <label>
      {label}
      <input
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={described || undefined}
        {...input}
      />
      {hint && (
        <span id={`${id}-hint`} className="hint">
          {hint}
        </span>
      )}
      <FieldError id={`${id}-error`} message={error} />
    </label>
  );
}
