# @dnk/ui

Shared official Shadcn Vue source components, New York/neutral, Tailwind CSS 4,
Reka UI and Lucide. Components were installed with `shadcn-vue add`, configured
by `components.json`. CORE control sizes are adapted to at least 44 px; tokens
and local Inter fonts live in `core/src/accounts/static/core/theme.css`.

Nuxt imports `@dnk/ui/components/button`, etc., and `@dnk/ui/style.css`.
The runtime console retains its own UI and is not migrated by this package.

`npm run build:accounts` from `frontends/` builds `src/django/main.ts` through
Vite into Django static assets, with hashed filenames and `manifest.json`.
Django's `accounts_assets` tag resolves these through staticfiles storage.
Run `npm run lint:ui` and `npm run typecheck:ui` before building.

## Server form enhancement

`core_fields`/`core_field` render normal Django HTML and escaped `json_script`
metadata. Hidden inputs remain server-owned. `FieldControl.vue` upgrades visible
fields using their names, IDs, constraints, labels, errors and current DOM values.
Passwords are excluded from JSON. Inputs use local state only; there is no auth
API or token storage in this bundle. HTML is not evaluated from field metadata.
Checkboxes retain a native input for allauth's `.checked` and change-event
contract; radio groups retain native form submission. Six-digit delivery codes
use InputOTP; the mixed MFA input remains unrestricted for recovery codes.

The small override of `account/js/onload.js` waits for UI readiness before
subscribing allauth handlers, once. On asset failure a bounded fallback keeps the
native forms usable. The document submit guard preserves the clicked submitter,
resets on browser return and allows retry; WebAuthn errors reset busy controls.

Source changes to official components should remain small and documented.
Use `npx shadcn-vue@latest diff --cwd packages/ui` to review upstream updates;
do not overwrite the 44px size adjustments without reviewing accessibility.
