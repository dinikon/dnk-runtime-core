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
- Displays runtime objects in the main console.
- Provides settings screens for the current user profile and workspace data model.
- Allows custom object and custom field creation and deletion through the schema registry API.

## Main Flows

The login page renders the auth layout and auth flow. The flow resolves the
tenant, requests an email OTP, confirms the OTP and then loads the current user
before redirecting to the console home page.

The console home page renders the main application layout. The sidebar exposes
the current workspace navigation and keeps unavailable sections visible as
disabled entries. The page content shows the object browser, which loads
available runtime objects. Shared runtime-record components remain available, but no generic custom-record API client
is currently wired.

The settings pages render their own settings layout. Profile settings update the
current user's profile through the identity API. Data model settings list runtime
objects, describe an object schema, create custom objects, create custom fields
and delete custom objects or fields.

Placeholder settings routes remain registered so direct links still render a
settings page, but those routes are not linked from the settings sidebar.

## Internal Structure

- `frontends/apps/console/src/app/`: Vue application shell, router and Pinia stores.
- `frontends/apps/console/src/app/providers/http/`: shared Axios client and HTTP error helpers.
- `frontends/apps/console/src/modules/`: feature modules with pages, API methods and backend contract types.
- `frontends/apps/console/src/layouts/`: app, settings and auth layout shells.
- `frontends/apps/console/src/components/ui/`: shadcn-vue style primitives.
- `frontends/apps/console/src/components/custom-ui/`: custom UI Kit components implemented from Figma.
- `frontends/apps/console/src/shared/config/`: shared frontend runtime configuration.

## API And Backend Contracts

The console uses a shared Axios client configured with `VITE_API_BASE_URL` and
`withCredentials: true`. If the environment variable is not set, the API base
URL defaults to `/api`. Backend methods and contract types live in their owning
`src/modules/*/api/` folders.

Current API modules:

- `authApi`: tenant resolve, email OTP request and confirmation, current user load and profile update.
- `schemaRegistryApi`: runtime object listing, object schema loading, custom object mutation and custom field mutation.
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

## Page Structure And Component Responsibilities

For page-oriented Vue modules, the route-level page component is an
orchestrator. It connects page state, queries, mutations, router concerns and
dialogs, then passes plain props down and handles emitted events back up.

The dependency shape should stay simple:

```text
Page
|-- Header
|-- Toolbar
|-- SearchBar
|-- Body
|   |-- Skeleton
|   |-- Empty
|   `-- Results
|       |-- List
|       |-- Grid / Cards
|       `-- Kanban
|-- Footer
|   |-- PagePagination
|   `-- InfinitePagination
`-- Forms / Dialogs
    |-- CreateDialog + Form
    |-- EditDialog + Form
    `-- DeleteDialog / ConfirmDialog
```

The core rule is:

```text
Page knows about all page collaborators.
Child components know only about their own props and emits.
UI components do not know about API clients, DTOs, router state or TanStack Query.
```

When a feature grows beyond a single small page, prefer this module shape:

```text
frontends/apps/console/src/modules/<feature>/
|-- api/
|   |-- <entity>.api.ts
|   |-- <entity>.dto.ts
|   `-- <entity>.mapper.ts
|-- model/
|   |-- <entity>.types.ts
|   |-- <entity>.constants.ts
|   |-- <entity>.query-keys.ts
|   |-- use-<entity-plural>-query.ts
|   |-- use-create-<entity>.ts
|   |-- use-update-<entity>.ts
|   |-- use-delete-<entity>.ts
|   `-- use-<entity-plural>-page-state.ts
|-- ui/
|   |-- page/
|   |-- results/
|   |-- item/
|   `-- forms/
`-- index.ts
```

Existing modules may still use `pages/`, `components/`, `queries/` and
`mutations/`; keep local consistency when making narrow changes. New or
substantially refactored modules should move toward the responsibility model
above.

Component responsibilities:

| Component | Responsibility |
| --- | --- |
| `[EntityPlural]Page.vue` | Route-level orchestrator. Owns page state, query/mutation wiring, router integration, dialog open state, event handling and data flow. It should not render cards, list rows, form fields or all loading/empty/result branches inline. |
| `[EntityPlural]Header.vue` | Page title, description and primary page action. It should not own search, filters or sorting. |
| `[EntityPlural]Toolbar.vue` | List actions such as view mode, sort, filters, bulk actions and refresh. |
| `[EntityPlural]SearchBar.vue` | Search input and search-related emits or `v-model`. Keep it separate when search is a first-class page control. |
| `[EntityPlural]Body.vue` | Chooses the current data state: `Skeleton`, `Empty`, `Error` or `Results`. List, grid and kanban components should not receive `loading` or `empty` props. |
| `[EntityPlural]Results.vue` | Chooses the concrete result view: `List`, `Grid` or `Kanban`. It represents loaded data, not pagination or fetching state. |
| `[EntityPlural]List.vue`, `[EntityPlural]Grid.vue`, `[EntityPlural]Kanban.vue` | Render collection layout only. They do not know how data is loaded, paginated, created, updated or deleted. |
| `[Entity]Card.vue`, `[Entity]ListItem.vue`, `[Entity]KanbanCard.vue` | Render one item. Use singular names for one entity and plural names for collections. |
| `[Entity]Form.vue` | Owns fields and validation. It emits submitted values and does not call API clients directly. |
| `Create[Entity]Dialog.vue`, `Edit[Entity]Dialog.vue` | Own modal UX, submit/cancel behavior and contain the form component. They emit submit events to the page or smart feature boundary. |
| `Delete[Entity]Dialog.vue` or `Delete[Entity]ConfirmDialog.vue` | Owns delete confirmation UX. Delete is a confirm dialog, not a form. |
| `[EntityPlural]Footer.vue` | Owns page navigation controls. Pagination belongs in the footer, not in `Results`. |

Shared UI components must remain free of business meaning. For example,
`shared/ui/pagination/PagePagination.vue` can render generic pagination, while
`[EntityPlural]Footer.vue` adapts that pagination to a feature's page state.

Keep DTOs and frontend models separate. DTOs live in `api/*.dto.ts`, mappers
translate them in `api/*.mapper.ts`, and Vue UI components consume frontend
types from `model/*.types.ts`. The UI layer may import child UI components,
shared UI primitives and model types, but it should not import `api`, DTOs,
mappers, query keys or query/mutation composables.

Use this quick naming check when adding a component:

```text
Route-level screen?              -> Page
Page block?                      -> Header / Toolbar / SearchBar / Body / Footer
Data state?                      -> Skeleton / Empty / Results
Concrete data view?              -> List / Grid / Kanban
One entity?                      -> Card / ListItem / KanbanCard
Input fields?                    -> Form
Modal action wrapper?            -> Dialog
Reusable UI without domain terms? -> shared/ui
```

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
- `frontends/apps/console/src/app/providers/http/`
- `frontends/apps/console/src/modules/`
- `frontends/apps/console/src/layouts/`
