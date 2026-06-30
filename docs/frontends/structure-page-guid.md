Финальный guide можно закрепить как стандарт для feature-модулей, где страница работает как оркестратор, а UI разбит по ролям.

# Vue Feature Module Guide: структура компонентов, зависимостей и именования

## 1. Главный принцип

Страница не должна быть местом, где находится вся реализация UI.

Страница — это **composition root** feature-модуля.

Она отвечает за сборку:

```txt
state + query + mutations + view components + dialogs
```

Компоненты ниже страницы должны быть узкими и отвечать только за свою роль.

Главное правило:

```txt
Page / CompositionRoot знает обо всех.
Дочерние компоненты знают только о своих props и emits.
UI-компоненты не знают про API, DTO, TanStack Query, router и transport layer.
```

---

# 2. Рекомендуемая структура файлов

Пример для модуля `workflow-applications`.

```txt
src/modules/workflow-applications/
├─ index.ts
│
├─ api/
│  ├─ workflow-application.api.ts
│  └─ workflow-application.dto.ts
│
├─ model/
│  ├─ workflow-application.types.ts
│  ├─ workflow-application.mapper.ts
│  ├─ workflow-application.constants.ts
│  ├─ workflow-application.query-keys.ts
│  │
│  ├─ use-workflow-applications-page-state.ts
│  ├─ use-workflow-applications-query.ts
│  ├─ use-create-workflow-application.ts
│  ├─ use-update-workflow-application.ts
│  └─ use-delete-workflow-application.ts
│
├─ ui/
│  ├─ page/
│  │  ├─ WorkflowApplicationsPage.vue
│  │  ├─ WorkflowApplicationsCompositionRoot.vue
│  │  ├─ WorkflowApplicationsPageHeader.vue
│  │  ├─ WorkflowApplicationsToolBar.vue
│  │  ├─ WorkflowApplicationsSearchPanel.vue
│  │  └─ WorkflowApplicationsNavigationPanel.vue
│  │
│  ├─ view-state/
│  │  ├─ WorkflowApplicationsViewState.vue
│  │  ├─ WorkflowApplicationsLoadingState.vue
│  │  ├─ WorkflowApplicationsEmptyState.vue
│  │  ├─ WorkflowApplicationsErrorState.vue
│  │  └─ WorkflowApplicationsResultSet.vue
│  │
│  ├─ result-set/
│  │  ├─ list-view/
│  │  │  ├─ WorkflowApplicationsListView.vue
│  │  │  ├─ WorkflowApplicationsListHeader.vue
│  │  │  ├─ workflow-applications-list-column-definition.ts
│  │  │  ├─ WorkflowApplicationsListItemView.vue
│  │  │  ├─ WorkflowApplicationsListItemSelector.vue
│  │  │  ├─ WorkflowApplicationsListItemFieldSet.vue
│  │  │  └─ WorkflowApplicationsListItemActionGroup.vue
│  │  │
│  │  ├─ card-collection-view/
│  │  │  ├─ WorkflowApplicationsCardCollectionView.vue
│  │  │  ├─ WorkflowApplicationCardView.vue
│  │  │  ├─ WorkflowApplicationCardHeader.vue
│  │  │  ├─ WorkflowApplicationCardContent.vue
│  │  │  ├─ WorkflowApplicationCardFooter.vue
│  │  │  └─ WorkflowApplicationCardActionGroup.vue
│  │  │
│  │  └─ kanban-board-view/
│  │     ├─ WorkflowApplicationsKanbanBoardView.vue
│  │     ├─ WorkflowApplicationsKanbanColumn.vue
│  │     ├─ WorkflowApplicationsKanbanColumnHeader.vue
│  │     ├─ WorkflowApplicationsKanbanColumnContent.vue
│  │     ├─ WorkflowApplicationKanbanCard.vue
│  │     ├─ WorkflowApplicationKanbanCardContent.vue
│  │     └─ WorkflowApplicationKanbanCardActionGroup.vue
│  │
│  └─ mutation/
│     ├─ WorkflowApplicationCreationDialog.vue
│     ├─ WorkflowApplicationUpdateDialog.vue
│     ├─ WorkflowApplicationDeletionDialog.vue
│     └─ WorkflowApplicationMutationForm.vue
│
└─ routes.ts
```

---

# 3. Shared UI структура

Feature-модуль не должен хранить универсальные UI-компоненты внутри себя.

Общие компоненты выносятся в `shared`.

```txt
src/shared/ui/
├─ pagination/
│  ├─ PagePagination.vue
│  └─ InfinitePagination.vue
│
├─ empty-state/
│  └─ EmptyState.vue
│
├─ error-state/
│  └─ ErrorState.vue
│
├─ loading-state/
│  └─ LoadingState.vue
│
├─ search/
│  └─ SearchInput.vue
│
└─ confirmation/
   └─ ConfirmationDialog.vue
```

Feature-компоненты используют shared-компоненты, но дают им бизнес-контекст.

Например:

```txt
shared/ui/pagination/InfinitePagination.vue
```

ничего не знает про `WorkflowApplication`.

А:

```txt
WorkflowApplicationsNavigationPanel.vue
```

знает, что пагинация используется для страницы workflow applications.

---

# 4. Дерево зависимостей компонентов

Финальное дерево компонентов:

```txt
WorkflowApplicationsPage.vue
└─ WorkflowApplicationsCompositionRoot.vue
   ├─ WorkflowApplicationsPageHeader.vue
   │
   ├─ WorkflowApplicationsToolBar.vue
   │
   ├─ WorkflowApplicationsSearchPanel.vue
   │
   ├─ WorkflowApplicationsViewState.vue
   │  ├─ WorkflowApplicationsLoadingState.vue
   │  ├─ WorkflowApplicationsEmptyState.vue
   │  ├─ WorkflowApplicationsErrorState.vue
   │  └─ WorkflowApplicationsResultSet.vue
   │     ├─ WorkflowApplicationsListView.vue
   │     │  ├─ WorkflowApplicationsListHeader.vue
   │     │  └─ WorkflowApplicationsListItemView.vue
   │     │     ├─ WorkflowApplicationsListItemSelector.vue
   │     │     ├─ WorkflowApplicationsListItemFieldSet.vue
   │     │     └─ WorkflowApplicationsListItemActionGroup.vue
   │     │
   │     ├─ WorkflowApplicationsCardCollectionView.vue
   │     │  └─ WorkflowApplicationCardView.vue
   │     │     ├─ WorkflowApplicationCardHeader.vue
   │     │     ├─ WorkflowApplicationCardContent.vue
   │     │     ├─ WorkflowApplicationCardFooter.vue
   │     │     └─ WorkflowApplicationCardActionGroup.vue
   │     │
   │     └─ WorkflowApplicationsKanbanBoardView.vue
   │        ├─ WorkflowApplicationsKanbanColumn.vue
   │        │  ├─ WorkflowApplicationsKanbanColumnHeader.vue
   │        │  ├─ WorkflowApplicationsKanbanColumnContent.vue
   │        │  └─ WorkflowApplicationKanbanCard.vue
   │        │     ├─ WorkflowApplicationKanbanCardContent.vue
   │        │     └─ WorkflowApplicationKanbanCardActionGroup.vue
   │
   ├─ WorkflowApplicationsNavigationPanel.vue
   │  ├─ PagePagination.vue
   │  └─ InfinitePagination.vue
   │
   ├─ WorkflowApplicationCreationDialog.vue
   │  └─ WorkflowApplicationMutationForm.vue
   │
   ├─ WorkflowApplicationUpdateDialog.vue
   │  └─ WorkflowApplicationMutationForm.vue
   │
   └─ WorkflowApplicationDeletionDialog.vue
```

---

# 5. Роли компонентов

## `WorkflowApplicationsPage.vue`

Route-level компонент.

Его задача — подключить страницу к роутингу.

Может быть тонким wrapper-компонентом:

```txt
WorkflowApplicationsPage.vue
└─ WorkflowApplicationsCompositionRoot.vue
```

Если проект небольшой, можно объединить `Page` и `CompositionRoot`, но лучше разделять.

---

## `WorkflowApplicationsCompositionRoot.vue`

Главный оркестратор feature-модуля.

Отвечает за:

```txt
- page state
- query params
- загрузку данных
- mutations
- открытие/закрытие dialogs
- передачу props вниз
- обработку emits вверх
```

Не отвечает за:

```txt
- разметку карточки
- разметку списка
- состояние Empty/Skeleton/Error
- валидацию формы на уровне UI-полей
- внутреннюю структуру List/Grid/Kanban
```

---

## `WorkflowApplicationsPageHeader.vue`

Компонент идентичности страницы.

Заменяет обычный `Header`.

Отвечает за:

```txt
- title
- description
- primary action
- contextual metadata
```

Пример:

```txt
Title: Workflow Applications
Description: Manage workflow application flows
Action: Create application
```

---

## `WorkflowApplicationsToolBar.vue`

Панель управления коллекцией.

Заменяет обычный `Toolbar`.

Отвечает за:

```txt
- view mode: list / cards / kanban
- sorting
- filters
- refresh
- bulk actions
- secondary actions
```

---

## `WorkflowApplicationsSearchPanel.vue`

Панель запроса данных.

Заменяет обычный `SearchBar`.

Отвечает за:

```txt
- search
- advanced search
- quick filters
- saved query presets
```

Если сейчас есть только один search input, компонент всё равно можно назвать `SearchPanel`, потому что в будущем он может расшириться.

---

## `WorkflowApplicationsViewState.vue`

Компонент состояния представления.

Отвечает за выбор UI-состояния:

```txt
loading → WorkflowApplicationsLoadingState
empty   → WorkflowApplicationsEmptyState
error   → WorkflowApplicationsErrorState
success → WorkflowApplicationsResultSet
```

Этот компонент не должен знать, как устроены карточки, строки списка или kanban.

---

## `WorkflowApplicationsResultSet.vue`

Компонент успешного набора данных.

Отвечает за выбор способа отображения результата:

```txt
list   → WorkflowApplicationsListView
cards  → WorkflowApplicationsCardCollectionView
kanban → WorkflowApplicationsKanbanBoardView
```

`ResultSet` — это не список и не карточки. Это абстракция над успешно загруженной коллекцией.

---

## `WorkflowApplicationsNavigationPanel.vue`

Панель навигации по результатам.

Заменяет обычный `Footer`.

Отвечает за:

```txt
- page pagination
- infinite pagination
- load more
- page size
- total count
```

Пагинация не должна находиться внутри `ResultSet`.

`ResultSet` показывает данные.

`NavigationPanel` управляет навигацией по данным.

---

# 6. ResultSet и внутренние виды отображения

`WorkflowApplicationsResultSet.vue` может отображать данные в разных видах:

```txt
ListView
CardCollectionView
KanbanBoardView
```

Каждый вид имеет свою внутреннюю композицию.

---

## 6.1. Card Collection View

Карточное представление используется, когда один item отображается как самостоятельная карточка.

```txt
WorkflowApplicationsCardCollectionView.vue
└─ WorkflowApplicationCardView.vue
   ├─ WorkflowApplicationCardHeader.vue
   ├─ WorkflowApplicationCardContent.vue
   ├─ WorkflowApplicationCardFooter.vue
   └─ WorkflowApplicationCardActionGroup.vue
```

### `WorkflowApplicationsCardCollectionView.vue`

Отвечает за:

```txt
- layout коллекции карточек
- grid/flex структуру
- render массива items
- проброс событий наружу
```

Не отвечает за:

```txt
- loading
- empty
- pagination
- API
- mutation
```

---

### `WorkflowApplicationCardView.vue`

Одна карточка сущности.

Отвечает за композицию карточки:

```txt
Header + Content + Footer + Actions
```

---

### `WorkflowApplicationCardHeader.vue`

Отвечает за верхнюю часть карточки:

```txt
- icon
- title
- subtitle
- status badge
```

---

### `WorkflowApplicationCardContent.vue`

Отвечает за основное содержимое карточки:

```txt
- description
- kind
- metadata
- counters
- short summary
```

---

### `WorkflowApplicationCardFooter.vue`

Отвечает за нижнюю часть карточки:

```txt
- createdAt
- updatedAt
- owner
- secondary metadata
```

---

### `WorkflowApplicationCardActionGroup.vue`

Группа действий над карточкой:

```txt
- edit
- duplicate
- archive
- delete
```

---

## 6.2. List View

Списочное представление используется, когда коллекция отображается строками.

```txt
WorkflowApplicationsListView.vue
├─ WorkflowApplicationsListHeader.vue
├─ workflow-applications-list-column-definition.ts
└─ WorkflowApplicationsListItemView.vue
   ├─ WorkflowApplicationsListItemSelector.vue
   ├─ WorkflowApplicationsListItemFieldSet.vue
   └─ WorkflowApplicationsListItemActionGroup.vue
```

### `WorkflowApplicationsListView.vue`

Контейнер списка.

Отвечает за:

```txt
- структуру списка
- render массива items
- передачу item в ListItemView
- проброс событий наружу
```

Не отвечает за:

```txt
- loading
- empty
- pagination
- API
- mutation
```

---

### `WorkflowApplicationsListHeader.vue`

Шапка списка.

Отвечает за:

```txt
- названия колонок
- общий selector
- сортировку по колонкам
- отображение column actions
```

---

### `workflow-applications-list-column-definition.ts`

Конфигурация колонок списка.

Пример:

```ts
export const workflowApplicationListColumns = [
  {
    key: "title",
    label: "Title",
    sortable: true,
  },
  {
    key: "status",
    label: "Status",
    sortable: true,
  },
  {
    key: "createdAt",
    label: "Created at",
    sortable: true,
  },
];
```

---

### `WorkflowApplicationsListItemView.vue`

Один элемент списка.

Отвечает за композицию строки:

```txt
Selector + FieldSet + ActionGroup
```

---

### `WorkflowApplicationsListItemSelector.vue`

Отвечает за выбор одного элемента.

Используется для:

```txt
- checkbox
- multi select
- bulk actions
```

---

### `WorkflowApplicationsListItemFieldSet.vue`

Набор отображаемых полей строки.

Например:

```txt
- title
- description
- status
- kind
- createdAt
```

---

### `WorkflowApplicationsListItemActionGroup.vue`

Действия над строкой:

```txt
- edit
- open
- duplicate
- delete
```

---

## 6.3. Kanban Board View

Kanban-представление используется, когда items группируются по статусу, этапу или состоянию.

```txt
WorkflowApplicationsKanbanBoardView.vue
└─ WorkflowApplicationsKanbanColumn.vue
   ├─ WorkflowApplicationsKanbanColumnHeader.vue
   ├─ WorkflowApplicationsKanbanColumnContent.vue
   └─ WorkflowApplicationKanbanCard.vue
      ├─ WorkflowApplicationKanbanCardContent.vue
      └─ WorkflowApplicationKanbanCardActionGroup.vue
```

### `WorkflowApplicationsKanbanBoardView.vue`

Контейнер kanban-доски.

Отвечает за:

```txt
- раскладку колонок
- группировку items по колонкам
- передачу items в columns
```

---

### `WorkflowApplicationsKanbanColumn.vue`

Одна колонка kanban.

Отвечает за:

```txt
- column identity
- column content
- список карточек внутри колонки
```

---

### `WorkflowApplicationsKanbanColumnHeader.vue`

Шапка kanban-колонки.

Отвечает за:

```txt
- название колонки
- количество items
- column actions
```

---

### `WorkflowApplicationsKanbanColumnContent.vue`

Контент kanban-колонки.

Отвечает за:

```txt
- render карточек
- empty внутри конкретной колонки
- drop zone, если есть drag-and-drop
```

---

### `WorkflowApplicationKanbanCard.vue`

Карточка item внутри kanban.

Может быть проще, чем обычная `CardView`.

---

# 7. Формы и mutation components

Формы и диалоги не должны смешиваться.

```txt
Dialog = shell действия
Form = поля и валидация
Mutation = create/update/delete operation
```

Структура:

```txt
mutation/
├─ WorkflowApplicationCreationDialog.vue
├─ WorkflowApplicationUpdateDialog.vue
├─ WorkflowApplicationDeletionDialog.vue
└─ WorkflowApplicationMutationForm.vue
```

---

## `WorkflowApplicationCreationDialog.vue`

Диалог создания.

Отвечает за:

```txt
- open / close
- title dialog
- submit action
- использование WorkflowApplicationMutationForm
```

Не вызывает API напрямую, если mutation находится в CompositionRoot.

---

## `WorkflowApplicationUpdateDialog.vue`

Диалог редактирования.

Отвечает за:

```txt
- open / close
- initial values
- submit updated payload
- использование WorkflowApplicationMutationForm
```

---

## `WorkflowApplicationDeletionDialog.vue`

Диалог удаления.

Это не form.

Отвечает за:

```txt
- confirmation
- warning text
- confirm / cancel
```

---

## `WorkflowApplicationMutationForm.vue`

Общая форма для create/update.

Отвечает за:

```txt
- fields
- local validation
- form submit event
```

Не отвечает за:

```txt
- API call
- query invalidation
- closing dialog after success
- toast notification after mutation
```

---

# 8. Дерево зависимостей по слоям

Правильное направление зависимостей:

```txt
shared
  ↑
api
  ↑
model
  ↑
ui
  ↑
composition root
  ↑
route page
```

Практически:

```txt
WorkflowApplicationsPage.vue
  imports WorkflowApplicationsCompositionRoot.vue

WorkflowApplicationsCompositionRoot.vue
  imports model composables
  imports page/view/dialog components

model composables
  import api functions
  import mapper
  import query keys

api
  imports http client
  works with DTO

ui components
  import model types
  import shared/ui components
  do not import api
```

---

# 9. Allowed imports

## `api/`

Может импортировать:

```txt
- shared http client
- DTO types
```

Не должен импортировать:

```txt
- Vue components
- page state
- UI
- TanStack Query hooks
```

---

## `model/`

Может импортировать:

```txt
- api functions
- DTO types
- mapper
- TanStack Query
- Vue reactivity
```

Не должен импортировать:

```txt
- .vue components
- route-level components
- UI components
```

---

## `ui/`

Может импортировать:

```txt
- own child components
- shared/ui components
- model types
- constants
```

Не должен импортировать:

```txt
- api functions
- DTO directly
- TanStack Query hooks
- router directly
```

Исключение возможно только для очень простых smart-components, но для чистой архитектуры лучше избегать.

---

## `CompositionRoot`

Может импортировать:

```txt
- model composables
- mutations
- query hooks
- page state
- ui components
```

Это единственный компонент, где допустимо соединять бизнес-состояние и UI.

---

# 10. Data flow

Данные идут сверху вниз через props.

События идут снизу вверх через emits.

```txt
CompositionRoot
  ↓ props
ViewState
  ↓ props
ResultSet
  ↓ props
ListView / CardCollectionView / KanbanBoardView
  ↓ props
Item components

Item components
  ↑ emit edit/delete/select
View components
  ↑ re-emit
ResultSet
  ↑ re-emit
ViewState
  ↑ re-emit
CompositionRoot
```

Пример событий:

```txt
WorkflowApplicationCardActionGroup.vue
  emits: edit, delete

WorkflowApplicationCardView.vue
  re-emits: edit, delete

WorkflowApplicationsCardCollectionView.vue
  re-emits: edit, delete

WorkflowApplicationsResultSet.vue
  re-emits: edit, delete

WorkflowApplicationsViewState.vue
  re-emits: edit, delete

WorkflowApplicationsCompositionRoot.vue
  handles: edit, delete
```

---

# 11. Naming rules

## 11.1. Entity naming

Для коллекции используется plural:

```txt
WorkflowApplications
Contacts
Campaigns
Broadcasts
```

Для одного элемента используется singular:

```txt
WorkflowApplication
Contact
Campaign
Broadcast
```

Правильно:

```txt
WorkflowApplicationsListView.vue
WorkflowApplicationCardView.vue
```

Неправильно:

```txt
WorkflowApplicationListView.vue
WorkflowApplicationsCardView.vue
```

---

## 11.2. Page-level components

```txt
[EntityPlural]Page.vue
[EntityPlural]CompositionRoot.vue
[EntityPlural]PageHeader.vue
[EntityPlural]ToolBar.vue
[EntityPlural]SearchPanel.vue
[EntityPlural]NavigationPanel.vue
```

Примеры:

```txt
WorkflowApplicationsPage.vue
WorkflowApplicationsCompositionRoot.vue
WorkflowApplicationsPageHeader.vue
WorkflowApplicationsToolBar.vue
WorkflowApplicationsSearchPanel.vue
WorkflowApplicationsNavigationPanel.vue
```

---

## 11.3. View state components

```txt
[EntityPlural]ViewState.vue
[EntityPlural]LoadingState.vue
[EntityPlural]EmptyState.vue
[EntityPlural]ErrorState.vue
[EntityPlural]ResultSet.vue
```

Примеры:

```txt
WorkflowApplicationsViewState.vue
WorkflowApplicationsLoadingState.vue
WorkflowApplicationsEmptyState.vue
WorkflowApplicationsErrorState.vue
WorkflowApplicationsResultSet.vue
```

---

## 11.4. Result view components

```txt
[EntityPlural]ListView.vue
[EntityPlural]CardCollectionView.vue
[EntityPlural]KanbanBoardView.vue
```

Примеры:

```txt
WorkflowApplicationsListView.vue
WorkflowApplicationsCardCollectionView.vue
WorkflowApplicationsKanbanBoardView.vue
```

---

## 11.5. Item-level components

```txt
[EntitySingular]CardView.vue
[EntitySingular]CardHeader.vue
[EntitySingular]CardContent.vue
[EntitySingular]CardFooter.vue
[EntitySingular]CardActionGroup.vue
```

Примеры:

```txt
WorkflowApplicationCardView.vue
WorkflowApplicationCardHeader.vue
WorkflowApplicationCardContent.vue
WorkflowApplicationCardFooter.vue
WorkflowApplicationCardActionGroup.vue
```

---

## 11.6. List item components

Для списка можно использовать plural prefix, потому что элемент принадлежит конкретному списочному представлению:

```txt
[EntityPlural]ListItemView.vue
[EntityPlural]ListItemSelector.vue
[EntityPlural]ListItemFieldSet.vue
[EntityPlural]ListItemActionGroup.vue
```

Примеры:

```txt
WorkflowApplicationsListItemView.vue
WorkflowApplicationsListItemSelector.vue
WorkflowApplicationsListItemFieldSet.vue
WorkflowApplicationsListItemActionGroup.vue
```

---

## 11.7. Form and dialog components

```txt
[EntitySingular]CreationDialog.vue
[EntitySingular]UpdateDialog.vue
[EntitySingular]DeletionDialog.vue
[EntitySingular]MutationForm.vue
```

Примеры:

```txt
WorkflowApplicationCreationDialog.vue
WorkflowApplicationUpdateDialog.vue
WorkflowApplicationDeletionDialog.vue
WorkflowApplicationMutationForm.vue
```

---

# 12. Pagination rules

Пагинация не должна быть внутри:

```txt
ListView
CardCollectionView
KanbanBoardView
ResultSet
```

Пагинация должна быть в:

```txt
WorkflowApplicationsNavigationPanel.vue
```

Внутри можно подключать shared-компоненты:

```txt
PagePagination.vue
InfinitePagination.vue
```

Пример логики:

```txt
paginationMode === "page"
  → PagePagination

paginationMode === "infinite"
  → InfinitePagination
```

---

# 13. Page state

Состояние страницы лучше держать отдельно:

```txt
model/use-workflow-applications-page-state.ts
```

Оно может содержать:

```txt
- search
- filters
- sort
- viewMode
- paginationMode
- page
- limit
- cursor
- selectedIds
```

Пример:

```ts
export type WorkflowApplicationsViewMode =
  | "list"
  | "cards"
  | "kanban";

export type WorkflowApplicationsPaginationMode =
  | "page"
  | "infinite";

export function useWorkflowApplicationsPageState() {
  const search = ref("");
  const viewMode = ref<WorkflowApplicationsViewMode>("cards");
  const paginationMode = ref<WorkflowApplicationsPaginationMode>("infinite");

  const page = ref(1);
  const limit = ref(20);
  const selectedIds = ref<string[]>([]);

  const queryParams = computed(() => ({
    search: search.value,
    page: page.value,
    limit: limit.value,
  }));

  return {
    search,
    viewMode,
    paginationMode,
    page,
    limit,
    selectedIds,
    queryParams,
  };
}
```

---

# 14. DTO, mapper and frontend types

DTO не должен попадать в UI.

```txt
api DTO → mapper → frontend model type → UI
```

Пример:

```txt
api/workflow-application.dto.ts
model/workflow-application.mapper.ts
model/workflow-application.types.ts
```

## DTO

```ts
export interface WorkflowApplicationListItemDto {
  id: string;
  created_at: string;
  kind: string;
  status: string;
  title: string;
  description: string | null;
  icon: string;
  icon_background: string;
}
```

## Frontend type

```ts
export interface WorkflowApplicationListItem {
  id: string;
  createdAt: string;
  kind: WorkflowApplicationKind;
  status: WorkflowApplicationStatus;
  title: string;
  description: string | null;
  icon: string;
  iconBackground: string;
}
```

## Mapper

```ts
export function mapWorkflowApplicationListItem(
  dto: WorkflowApplicationListItemDto,
): WorkflowApplicationListItem {
  return {
    id: dto.id,
    createdAt: dto.created_at,
    kind: dto.kind as WorkflowApplicationKind,
    status: dto.status as WorkflowApplicationStatus,
    title: dto.title,
    description: dto.description,
    icon: dto.icon,
    iconBackground: dto.icon_background,
  };
}
```

---

# 15. Practical dependency rules

## Rule 1

`CompositionRoot` может быть большим по импортам, но не должен быть большим по template.

Он собирает зависимости, но не рисует детальный UI.

---

## Rule 2

`ViewState` отвечает только за:

```txt
Loading / Empty / Error / Success
```

Он не отвечает за:

```txt
List / Card / Kanban layout
```

---

## Rule 3

`ResultSet` отвечает только за выбор view mode:

```txt
ListView / CardCollectionView / KanbanBoardView
```

Он не отвечает за:

```txt
loading / empty / error / pagination
```

---

## Rule 4

`ListView`, `CardCollectionView`, `KanbanBoardView` отвечают только за отображение items.

Они не знают:

```txt
- откуда пришли items
- как работает pagination
- как работает API
- как работает query invalidation
```

---

## Rule 5

`CardView` отвечает только за один item.

Он не должен знать:

```txt
- список
- пагинацию
- фильтры
- search
- общий page state
```

---

## Rule 6

`MutationForm` не вызывает API.

Она только собирает данные и делает:

```txt
emit("submit", payload)
```

---

## Rule 7

`CreationDialog`, `UpdateDialog`, `DeletionDialog` не должны знать про TanStack Query.

Они получают:

```txt
- open
- saving/deleting
- initial values
```

И возвращают события:

```txt
- submit
- confirm
- close
```

---

# 16. Финальная рекомендуемая структура для проекта

Для production-кода я бы использовал такой вариант:

```txt
src/modules/workflow-applications/
├─ api/
│  ├─ workflow-application.api.ts
│  └─ workflow-application.dto.ts
│
├─ model/
│  ├─ workflow-application.types.ts
│  ├─ workflow-application.mapper.ts
│  ├─ workflow-application.constants.ts
│  ├─ workflow-application.query-keys.ts
│  ├─ use-workflow-applications-page-state.ts
│  ├─ use-workflow-applications-query.ts
│  ├─ use-create-workflow-application.ts
│  ├─ use-update-workflow-application.ts
│  └─ use-delete-workflow-application.ts
│
├─ ui/
│  ├─ page/
│  │  ├─ WorkflowApplicationsPage.vue
│  │  ├─ WorkflowApplicationsCompositionRoot.vue
│  │  ├─ WorkflowApplicationsPageHeader.vue
│  │  ├─ WorkflowApplicationsToolBar.vue
│  │  ├─ WorkflowApplicationsSearchPanel.vue
│  │  └─ WorkflowApplicationsNavigationPanel.vue
│  │
│  ├─ view-state/
│  │  ├─ WorkflowApplicationsViewState.vue
│  │  ├─ WorkflowApplicationsLoadingState.vue
│  │  ├─ WorkflowApplicationsEmptyState.vue
│  │  ├─ WorkflowApplicationsErrorState.vue
│  │  └─ WorkflowApplicationsResultSet.vue
│  │
│  ├─ result-set/
│  │  ├─ list-view/
│  │  ├─ card-collection-view/
│  │  └─ kanban-board-view/
│  │
│  └─ mutation/
│     ├─ WorkflowApplicationCreationDialog.vue
│     ├─ WorkflowApplicationUpdateDialog.vue
│     ├─ WorkflowApplicationDeletionDialog.vue
│     └─ WorkflowApplicationMutationForm.vue
│
├─ routes.ts
└─ index.ts
```

---

# 17. Короткая формула архитектуры

```txt
CompositionRoot
  управляет состоянием и данными

ViewState
  выбирает состояние интерфейса

ResultSet
  выбирает способ отображения результата

ListView / CardCollectionView / KanbanBoardView
  отображают коллекцию

ItemView / CardView / KanbanCard
  отображают один элемент

Dialog
  управляет сценарием действия

Form
  собирает данные

NavigationPanel
  управляет пагинацией
```

Главная идея:

```txt
Название компонента должно описывать его роль в системе,
а не только его визуальное расположение на странице.
```
