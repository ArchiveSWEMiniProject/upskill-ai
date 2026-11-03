"use client";

// Loads and edits one list of profile entries (courses, projects) through the
// API's list / add / replace / delete routes.
import { useCallback, useEffect, useState } from "react";

import { api } from "./api";
import { errorMessage, type FieldErrors, fieldErrors } from "./forms";

export type SaveResult = { ok: true } | { ok: false; errors: FieldErrors; message: string };

export function useEntries<T>(
  path: string,
  idOf: (entry: T) => number,
  onUnauthorized: (status: number) => void,
) {
  const [entries, setEntries] = useState<T[] | null>(null);
  const [error, setError] = useState("");

  const failed = useCallback(
    (status: number, data: unknown): string => {
      if (status === 401 || status === 403) onUnauthorized(status);
      return errorMessage(data);
    },
    [onUnauthorized],
  );

  useEffect(() => {
    api<T[]>(path).then(({ status, data }) => {
      if (status === 200) setEntries(data);
      else setError(failed(status, data));
    });
  }, [path, failed]);

  // Adds when id is undefined, otherwise replaces that entry.
  async function save(body: unknown, id?: number): Promise<SaveResult> {
    const { status, data } = await api<T>(id === undefined ? path : `${path}/${id}`, {
      method: id === undefined ? "POST" : "PUT",
      json: body,
    });
    if (status === 200 || status === 201) {
      setEntries((current) =>
        id === undefined
          ? [...(current ?? []), data]
          : (current ?? []).map((entry) => (idOf(entry) === id ? data : entry)),
      );
      return { ok: true };
    }
    if (status === 422) {
      return { ok: false, errors: fieldErrors((data as any)?.detail), message: "" };
    }
    return { ok: false, errors: {}, message: failed(status, data) };
  }

  async function remove(id: number): Promise<boolean> {
    const { status, data } = await api(`${path}/${id}`, { method: "DELETE" });
    if (status === 204 || status === 404) {
      setEntries((current) => (current ?? []).filter((entry) => idOf(entry) !== id));
      return true;
    }
    setError(failed(status, data));
    return false;
  }

  return { entries, error, save, remove };
}
