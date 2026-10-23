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

## Sign-in

The login card offers email OTP and dNiko cloud sign-in. Control Plane project
links add `auth_provider=cloud`; the router preserves this hint on the login
redirect and removes it from the destination. The login page consumes it before
starting a single silent OIDC attempt (`POST /api/auth/cloud/start/` with
`purpose: "login", silent: true`). This sends `prompt=none` to Control Plane.
An existing Runtime session opens the project directly. A failed attempt returns
to the email form without automatically retrying. The dNiko button starts the
normal interactive flow (`silent: false`, also the API default). Linking an
account never uses silent mode.

OTP delivery is controlled by the **backend** `DEPLOY_ENV`, independently of the
frontend build. Only `DEVELOPMENT` returns the development code and skips OTP
email delivery. All other values, including the default `PRODUCTION`, send the
email and omit the code from application results and HTTP responses. This applies
to both login and invitation OTPs; invitation notification emails are unchanged.
Login retains the existing success response on mail-delivery failure, allowing
the user to request a new code. Invitation delivery errors retain their existing
behavior.

Deploy the Runtime backend and console before updating Control Plane entry links.
No database migration is needed. Run navigation regressions with
`npm --workspace @dnk/console run test:auth` from `frontends/`.

## Source Of Truth

- `src/app/router.ts`
- `src/app/stores/tenant.ts`
- `src/app/stores/user.ts`
- `src/app/providers/http/`
- `src/modules/`
- `src/layouts/`
