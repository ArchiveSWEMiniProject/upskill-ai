// Error text shown under a field, or for the whole form. Renders nothing when
// there is no message, so screen readers announce only real errors.
export function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? (
    <span id={id} className="field-error">
      {message}
    </span>
  ) : null;
}

export function FormError({ message }: { message?: string }) {
  return message ? (
    <p className="form-error" role="alert">
      {message}
    </p>
  ) : null;
}
