"use client";

// Loads and edits one list of profile entries (courses, projects) through the
// API's list / add / replace / delete routes.
import { useCallback, useEffect, useRef, useState } from "react";

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
  // Counts finished saves and deletes, so a list that was requested before
  // one of them can be recognised as possibly missing it.
  const changes = useRef(0);

  const failed = useCallback(
    (status: number, data: unknown): string => {
      if (status === 401 || status === 403) onUnauthorized(status);
      return errorMessage(data);
    },
    [onUnauthorized],
  );

  useEffect(() => {
    let active = true;
    async function load() {
      for (;;) {
        const started = changes.current;
        const { status, data } = await api<T[]>(path);
        if (!active) return;
        if (status !== 200) {
          setError(failed(status, data));
          return;
        }
        // Showing this list would drop an entry saved while it loaded, so ask
        // again; the server has every finished change by now.
        if (changes.current === started) {
          setEntries(data);
          return;
        }
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [path, failed]);

  // Adds when id is undefined, otherwise replaces that entry.
  async function save(body: unknown, id?: number): Promise<SaveResult> {
    const { status, data } = await api<T>(id === undefined ? path : `${path}/${id}`, {
      method: id === undefined ? "POST" : "PUT",
      json: body,
    });
    if (status === 200 || status === 201) {
      changes.current += 1;
      setError("");
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
      changes.current += 1;
      setError("");
      setEntries((current) => (current ?? []).filter((entry) => idOf(entry) !== id));
      return true;
    }
    setError(failed(status, data));
    return false;
  }

  return { entries, error, save, remove };
}
