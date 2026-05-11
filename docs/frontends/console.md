# Console Frontend

## Purpose

The console frontend is the browser application for operating the runtime core
from an administrative workspace. It is implemented as a Vue 3 application in
the frontend workspace and talks to the backend HTTP API through typed client
modules.

## Public Functionality

- Resolves the current tenant before showing the login flow.
- Authenticates console users through email OTP.
- Loads and stores the current console user session.
- Displays runtime objects and object records in the main console.
- Provides settings screens for the current user profile and workspace data model.
- Allows custom object and custom field creation and deletion through the schema registry API.

## Main Flows

The login page renders the auth layout and auth flow. The flow resolves the
tenant, requests an email OTP, confirms the OTP and then loads the current user
before redirecting to the console home page.

The console home page renders the main application layout. The sidebar exposes
the current workspace navigation and keeps unavailable sections visible as
disabled entries. The page content shows the object browser, which loads
available runtime objects and then lists records for the selected object.

The settings pages render their own settings layout. Profile settings update the
current user's profile through the identity API. Data model settings list runtime
objects, describe an object schema, create custom objects, create custom fields
and delete custom objects or fields.

Placeholder settings routes remain registered so direct links still render a
settings page, but those routes are not linked from the settings sidebar.

## Internal Structure

- `frontends/apps/console/src/app/`: Vue application shell, router and Pinia stores.
- `frontends/apps/console/src/api/`: typed API modules grouped by backend area.
- `frontends/apps/console/src/features/`: feature-level page and component code.
- `frontends/apps/console/src/layouts/`: app, settings and auth layout shells.
- `frontends/apps/console/src/components/ui/`: shadcn-vue style primitives.
- `frontends/apps/console/src/components/custom-ui/`: custom UI Kit components implemented from Figma.
- `frontends/apps/console/src/shared/config/`: shared frontend runtime configuration.

## API And Backend Contracts

The console uses a shared Axios client configured with `VITE_API_BASE_URL` and
`withCredentials: true`. If the environment variable is not set, the API base
URL defaults to `/api`.

Current API modules:

- `identityApi`: tenant resolve, email OTP request and confirmation, current user load and profile update.
- `schemaRegistryApi`: runtime object listing, object schema loading, custom object mutation and custom field mutation.
- `objectRecordsApi`: object record listing for custom objects and configured standard objects.
- `crmContactsApi`: contact field description and contact CRUD helpers.

## Layout And UI System

The main console shell uses `AppLayout`, which renders a shadcn sidebar provider,
the app sidebar, a collapsible sidebar trigger and a page content slot.

Settings screens use `SettingsLayout`, which keeps the same shadcn sidebar
structure but has settings-specific navigation, breadcrumbs and an internal
scrolling content card.

Login uses `AuthLayout`, a centered viewport shell without a sidebar.

Reusable primitives live under `components/ui` and follow the shadcn-vue
composition style. Figma-specific custom components live under
`components/custom-ui`.

## State And Session

`useSessionStore` is the current session state boundary. It owns:

- tenant resolution state;
- current console user state;
- email OTP challenge state;
- auth and profile loading flags;
- profile update mutation behavior.

The store calls the identity API directly and keeps the frontend auth flow
independent from router metadata beyond the `/login` route entry.

## Commands And Environment

Run console commands from `frontends/`:

- `npm install`
- `npm run dev:console`
- `npm run build:console`
- `npm run preview:console`
- `npm run typecheck:console`

Optional environment:

- `VITE_API_BASE_URL`: backend API base URL. Defaults to `/api`.

## Quality And Verification

The primary static verification command is:

```bash
npm run typecheck:console
```

The production build command also runs type checking before Vite:

```bash
npm run build:console
```

If a local build fails before application compilation while loading Rollup's
native optional package, treat it as a local dependency installation issue and
repair the frontend `node_modules` installation before evaluating application
code changes.

## Related

- [Frontend workspace README](../../frontends/README.md)
- [Console app README](../../frontends/apps/console/README.md)
- [HTTP API](../interfaces/http-api.md)
- [Identity module](../modules/identity.md)
- [Schema Registry module](../modules/schema-registry.md)
- [Runtime schema](../data/runtime-schema.md)

## Source Of Truth

- `frontends/apps/console/src/app/router.ts`
- `frontends/apps/console/src/app/stores/session.ts`
- `frontends/apps/console/src/api/`
- `frontends/apps/console/src/features/`
- `frontends/apps/console/src/layouts/`
