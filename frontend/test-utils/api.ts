// Replaces fetch with canned API replies, keyed by "METHOD /path" (the path
// after /api/v1). A list of replies is used in order; the last one repeats.
type Reply = { status: number; body?: unknown };

export type Call = { method: string; path: string; body: any; headers: Record<string, string> };

export function mockApi(routes: Record<string, Reply | Reply[]>): Call[] {
  const calls: Call[] = [];
  global.fetch = jest.fn(async (url: RequestInfo | URL, init: RequestInit = {}) => {
    const method = init.method ?? "GET";
    const path = String(url).replace(/^\/api\/v1/, "");
    const body = typeof init.body === "string" ? JSON.parse(init.body) : init.body;
    calls.push({ method, path, body, headers: (init.headers ?? {}) as Record<string, string> });
    const route = routes[`${method} ${path}`];
    const reply = Array.isArray(route) ? (route.length > 1 ? route.shift() : route[0]) : route;
    if (!reply) throw new Error(`unexpected request ${method} ${path}`);
    return { status: reply.status, json: async () => reply.body } as unknown as Response;
  }) as typeof fetch;
  return calls;
}

export const PROFILE = {
  student_id: 7,
  name: "Asha Rao",
  education_level: "UG",
  target_role_id: null,
  created_at: "2026-10-28T10:00:00Z",
};

// Replies for the sections the profile page loads once the profile exists.
export const EMPTY_SECTIONS = {
  "GET /profile/courses": { status: 200, body: [] },
  "GET /profile/projects": { status: 200, body: [] },
};
