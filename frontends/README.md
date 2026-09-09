# Runtime frontends

Independent npm workspace for the tenant runtime applications:

- `apps/console`: administrative and operator console.
- `apps/shortlink`: short-link frontend package.
- `packages/api-client`: backend HTTP API client.
- `packages/config`: shared frontend configuration and typed constants.

Run from this directory with Node 24.11 or newer:

```sh
npm ci
npm run dev:console
npm run lint:console
npm run typecheck:console
npm run build:console
npm run preview:console
```

The root Compose `frontend` service serves the runtime console. Core's Nuxt
application and account UI are maintained in the separate dnk-control-plane
repository; no source files or npm packages from that checkout are needed here.

See [Console frontend](../docs/frontends/console.md).
