> Dynamic schema/object APIs remain removed. CRM uses static backend contracts and tenant tables. Inventory and its SKU workspace have been removed.

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
- Provides tenant-scoped Contact and Company management in CRM.
- Provides simple Catalog products with separate overview and section editor, enum attributes and independent locale editors.
- Provides price-list and partner-offer workflows.
- Provides profile and administrator-only workspace access-management screens.

## Main Flows

The login page renders the auth layout and auth flow. The flow resolves the
tenant, requests an email OTP, confirms the OTP and then loads the current user
before redirecting to the console home page.

The console home page renders the main application layout. The sidebar exposes
the current workspace navigation and keeps unavailable sections visible as
disabled entries. CRM has separate contact and company routes. Each CRM page owns
URL-backed search and pagination state, query/mutation wiring, and create, edit
and delete dialogs while collection and form components remain presentational.

Profile settings update the current user's profile through the identity API and
remain available from the user menu. Administrators enter a separate admin layout
through the tenant menu. The first admin screen manages users and invitations;
future admin navigation entries remain hidden until their pages are implemented.

## Internal Structure

- `frontends/apps/console/src/app/`: Vue application shell, router and Pinia stores.
- `frontends/apps/console/src/app/providers/http/`: shared Axios client and HTTP error helpers.
- `frontends/apps/console/src/modules/`: feature modules with pages, API methods and backend contract types.
- `frontends/apps/console/src/layouts/`: workspace, admin and auth layout shells.
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
- `crmContactsApi`: tenant-scoped contact list, search and CRUD.
- `crmCompaniesApi`: tenant-scoped company list, search and CRUD.
- `priceListsApi`: price-list setup, synchronization actions, offers and history.

## Layout And UI System

The main console shell uses `AppLayout`, which renders a shadcn sidebar provider,
the app sidebar, a collapsible sidebar trigger and a page content slot. For
administrators, the tenant header opens a menu that switches between the workspace
and `/admin/users`. Members keep the tenant header as a dashboard link.

Administrative screens use `AdminLayout`, with their own sidebar navigation,
breadcrumbs and content slot. Route metadata requires the `admin` role before the
layout is mounted. The sidebar exposes one Users link; member and invitation views
remain page-level tabs. The access page keeps tab, search, role and status state in
the URL and uses client-side filtering over the current identity API collections.

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

| Component                                                                      | Responsibility                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[EntityPlural]Page.vue`                                                       | Route-level orchestrator. Owns page state, query/mutation wiring, router integration, dialog open state, event handling and data flow. It should not render cards, list rows, form fields or all loading/empty/result branches inline. |
| `[EntityPlural]Header.vue`                                                     | Page title, description and primary page action. It should not own search, filters or sorting.                                                                                                                                         |
| `[EntityPlural]Toolbar.vue`                                                    | List actions such as view mode, sort, filters, bulk actions and refresh.                                                                                                                                                               |
| `[EntityPlural]SearchBar.vue`                                                  | Search input and search-related emits or `v-model`. Keep it separate when search is a first-class page control.                                                                                                                        |
| `[EntityPlural]Body.vue`                                                       | Chooses the current data state: `Skeleton`, `Empty`, `Error` or `Results`. List, grid and kanban components should not receive `loading` or `empty` props.                                                                             |
| `[EntityPlural]Results.vue`                                                    | Chooses the concrete result view: `List`, `Grid` or `Kanban`. It represents loaded data, not pagination or fetching state.                                                                                                             |
| `[EntityPlural]List.vue`, `[EntityPlural]Grid.vue`, `[EntityPlural]Kanban.vue` | Render collection layout only. They do not know how data is loaded, paginated, created, updated or deleted.                                                                                                                            |
| `[Entity]Card.vue`, `[Entity]ListItem.vue`, `[Entity]KanbanCard.vue`           | Render one item. Use singular names for one entity and plural names for collections.                                                                                                                                                   |
| `[Entity]Form.vue`                                                             | Owns fields and validation. It emits submitted values and does not call API clients directly.                                                                                                                                          |
| `Create[Entity]Dialog.vue`, `Edit[Entity]Dialog.vue`                           | Own modal UX, submit/cancel behavior and contain the form component. They emit submit events to the page or smart feature boundary.                                                                                                    |
| `Delete[Entity]Dialog.vue` or `Delete[Entity]ConfirmDialog.vue`                | Owns delete confirmation UX. Delete is a confirm dialog, not a form.                                                                                                                                                                   |
| `[EntityPlural]Footer.vue`                                                     | Owns page navigation controls. Pagination belongs in the footer, not in `Results`.                                                                                                                                                     |

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

`useTenantStore` and `useUserStore` are the current session boundaries. Together they own:

- tenant resolution state;
- current console user state;
- deduplicated current-user session bootstrap for protected route guards;
- email OTP challenge state;
- auth and profile loading flags;
- profile update mutation behavior.

The stores call the identity API directly and keep the frontend auth flow
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

## Catalog

MVP v1 supports simple standalone products only. The product routes are
`/catalog/items`, `/catalog/items/new`, `/catalog/items/:itemId` (overview),
and `/catalog/items/:itemId/edit` (section editor). Creation explicitly creates
a draft; there is no kind selector, variant filter, variant editor, structure
form or kind transition. Legacy kind/variant query parameters are removed and
`tab=variants` is normalized to `general`; nested variant routes are absent.

The product screens retain Console semantic tokens, existing shadcn-vue components,
a 1440 px content limit and a 320 px desktop sidebar. Overview shows safe HTML,
gallery, measurements, enum characteristics, classification, current price and
availability. The editor has general, inventory, shipping, attributes and additional
sections, plus localized texts, status, gallery, categories and tags.

`use-product-page` owns queries and the shared product draft. `ProductAutosave`
serializes PATCH writes after an 800 ms debounce. Only changed, valid sections are
sent; acknowledgement clears the submitted snapshot, never newer input. Refetches
update clean sections and retain unsaved edits. Catalog DTOs and form models have
no revisions. The other Catalog editors keep their explicit save buttons.

Attributes and options use stable IDs only. Lists, forms, product assignments and
overviews have no code field or code fallback. A label belongs to the explicitly
selected locale; missing translations show “Нет перевода”. Renaming, translating
and reordering preserve IDs and other translations. Existing options may be
reordered without filling a missing translation; new options require a label.
Attribute search uses the selected locale's label or the stable ID.

The editor has no section save/cancel buttons. One aria-live indicator reports
pending changes, saving, saved, field errors, or a paused queue. Invalid sections
remain editable while valid sections save. A server field error rolls back that
PATCH; the queue excludes the invalid section and resubmits the rest. Network/5xx
errors retain input and pause until the single Retry action is used. A 409 represents
a business conflict such as duplicate SKU, with a field error where available.

Navigation and locale changes flush the queue, then ask before discarding remaining
invalid or failed edits. Tabs retain the draft. Tenant/session changes clear drafts
and timers and ignore responses from the previous context. Closing a dirty or busy
tab triggers the browser's standard warning. Reload explicitly discards drafts.

Texts replace the full name/desc/short_desc dictionary with schema version. Name is
required; omitted optional blocks are deleted, explicit empty strings are retained.
Tiptap edits HTML, the backend sanitizes it and DOMPurify cleans the overview.
Characteristics/metadata are full sets; false/zero values and precise Decimal strings
are preserved. Units convert exact quantities. Gallery changes save automatically;
upload waits for them and uses the same write queue. Gallery controls pause during
upload; other fields remain editable. An ambiguous upload is not automatically
retried. Removing links retains Files objects.

`POST /items` creates a draft, `PATCH /items/{id}` edits it; old section endpoints
and `/items/simple` are absent. Omitted PATCH fields stay unchanged; nullable values
can be cleared explicitly. Concurrent edits to the same field or set use the last
successful write. Query keys retain tenant/item/locale/filter isolation.

Run `test:catalog` with Node 24 to check the autosave queue using the built-in test
runner; browser regression covers the rendered editor and real HTTP persistence.

Backend and Console must be released together because API contracts changed.
The new tenant migration `0026_catalog_attribute_ids` removes attribute and option
codes and their uniqueness constraints, preserving IDs, translations and product
assignments. Product SQL and future variable-product behavior are preserved in
the [Catalog plan](../plan/catalog.md). Release the migration with the new backend;
the previous backend still requires those columns. External Channels publications
continue to support their existing read capabilities.

## File Storage

`/files` shows tenant storage connections and private buckets. The system MinIO
connection carries `Default / System` and has no edit controls. Bucket statistics
show registered ready files and their total size. The page supports refresh,
loading, error and empty states; mobile view uses separate bucket cards.
Both data sources are authenticated read-only Files endpoints. File upload and
download belong to consuming business modules. See [Files](../modules/files.md).

## Related

- [Frontend workspace README](../../frontends/README.md)
- [Console app README](../../frontends/apps/console/README.md)
- [HTTP API](../interfaces/http-api.md)
- [Identity module](../modules/identity.md)
- [CRM module](../modules/crm.md)
- [Files module](../modules/files.md)
- [Contact points and reusable fields](../modules/contact-points.md)
- [Schema Registry module](../history/modules/schema-registry.md)
- [Runtime schema](../history/data/runtime-schema.md)

## Source Of Truth

- `frontends/apps/console/src/app/router.ts`
- `frontends/apps/console/src/app/stores/tenant.ts`
- `frontends/apps/console/src/app/stores/user.ts`
- `frontends/apps/console/src/app/providers/http/`
- `frontends/apps/console/src/modules/`
- `frontends/apps/console/src/layouts/`
