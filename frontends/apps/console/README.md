# Console Frontend

Administrative and operator console application built with Vue 3, Vite and TypeScript.

The full implementation notes live in the main project documentation:

- [Console frontend](../../../docs/frontends/console.md)

Run commands from `frontends/`:

- `npm run dev:console`
- `npm run build:console`
- `npm run preview:console`
- `npm run typecheck:console`

Optional environment:

- `VITE_API_BASE_URL`: backend API base URL. Defaults to `/api`.

## Source Of Truth

- `src/app/router.ts`
- `src/app/stores/session.ts`
- `src/api/`
- `src/features/`
- `src/layouts/`
