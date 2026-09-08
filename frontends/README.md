# Frontends

Workspace for frontend applications and shared frontend packages.

Current applications:

- `apps/core`: Nuxt application with a server-rendered public dNiko Alpha page and protected global account overview.
- `apps/console`: administrative and operator console.
- `apps/shortlink`: short link frontend experience.

Shared packages:

- `packages/api-client`: shared backend HTTP API client.
- `packages/ui`: reusable UI components.
- `packages/config`: shared frontend configuration and typed constants.

Console commands are run from this directory:

- `npm install`
- `npm run dev:console`
- `npm run build:console`
- `npm run preview:console`
- `npm run typecheck:console`

## Core

Run `npm ci`, then `npm run dev:core` and open `http://localhost:5174`.
Django must run on `localhost:8001`. Nuxt proxies `/api/`, `/accounts/`, `/admin/`
and `/static/` without changing the browser's Host header. The Core frontend
uses Django's session and CSRF protection; it does not use runtime console authentication.

Other commands: `npm run build:core`, `npm run typecheck:core`, `npm run lint:core`.
The shared theme and self-hosted Inter fonts are served by Django at `/static/core/`;
keep the Django proxy available when previewing the frontend.

The root Compose service `core-frontend` routes the application at
`http://localhost:8080` to the Nuxt server (`core-web`) and Django (`core`).
The public page includes server-rendered content and SEO metadata; private pages
are excluded from indexing and shared caches. The existing `frontend` service still serves the runtime console.
See [Core setup](../core/README.md) for authentication providers, migrations and HTTPS.

## Documentation

- [Console frontend](../docs/frontends/console.md)

## Source Of Truth

- `apps/console/src/`
- `apps/shortlink/`
- `packages/`
