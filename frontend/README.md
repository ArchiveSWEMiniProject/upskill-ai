# UpSkill-AI web app

A Next.js (React, TypeScript) app with one route group per module; `app/(m1)/` holds M1's pages
(log in and register at `/`, the student's profile at `/profile`).

The browser calls `/api/*` on the web app, which forwards it to the API, so the API needs no CORS
rules and the token is never sent to another origin. `API_URL` sets where the API is; it is fixed
into the rewrite when the app is built, and defaults to the compose service `http://upskill-api:8000`.

```
npm ci
API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
npm test                                     # Jest + React Testing Library
npm run typecheck
```

The tests run on every Docker image build (`frontend/Dockerfile`), so CI's Docker build stage fails
when they do.
