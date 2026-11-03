// Turns API errors into messages next to the fields they belong to.

export type FieldErrors = Record<string, string>;

type ValidationItem = { loc?: unknown; msg?: unknown };

// FastAPI reports a 422 as a list of {loc, msg} where loc is ["body", field].
// Returns {field: message}, keeping the first message for each field.
export function fieldErrors(detail: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (!Array.isArray(detail)) return errors;
  for (const item of detail as ValidationItem[]) {
    const loc = Array.isArray(item?.loc) ? item.loc : [];
    const field = loc[0] === "body" ? loc[1] : loc[0];
    if (typeof field === "string" && !(field in errors)) {
      errors[field] = cleanMessage(item.msg);
    }
  }
  return errors;
}

// Pydantic prefixes messages from custom validators with "Value error, ".
function cleanMessage(message: unknown): string {
  return String(message ?? "Invalid value").replace(/^Value error, /, "");
}

// The single message for a failed request that is not a field error.
export function errorMessage(data: unknown, fallback = "Something went wrong. Try again."): string {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  const message = (detail as { message?: unknown } | undefined)?.message;
  if (typeof message === "string") return message;
  return fallback;
}

// Form values as JSON: surrounding whitespace trimmed, blank optional fields
// sent as null so that editing can clear them.
export function formJson(
  entries: Iterable<[string, FormDataEntryValue]>,
  optional: string[] = [],
): Record<string, string | null> {
  const values: Record<string, string | null> = {};
  for (const [name, raw] of entries) {
    const value = typeof raw === "string" ? raw.trim() : raw.name;
    values[name] = value === "" && optional.includes(name) ? null : value;
  }
  return values;
}
