Страница Workflow должна выглядеть как **одна страница-оркестратор**, внутри которой переключаются 3 режима:

```txt
Edit  → редактирование графа, узлов, связей, настроек
View  → просмотр готового workflow без мутаций
Debug → запуск, трассировка, console, logs, состояние узлов
```

Правильная структура — не делать 3 разные страницы. Нужно сделать одну страницу:

```txt
WorkflowPage.vue
```

А режимы вынести внутрь:

```txt
WorkflowEditMode.vue
WorkflowViewMode.vue
WorkflowDebugMode.vue
```

## Рекомендуемая структура файлов

```txt
src/modules/workflow/
├─ index.ts
├─ routes.ts
│
├─ applications/
├─ analytics/
│
└─ workflows/
   ├─ api/
   │  ├─ workflow.api.ts
   │  └─ workflow.dto.ts
   │
   ├─ model/
   │  ├─ workflow.types.ts
   │  ├─ workflow-node.types.ts
   │  ├─ workflow-edge.types.ts
   │  ├─ workflow-mode.types.ts
   │  ├─ workflow-plugin.types.ts
   │  ├─ workflow-log.types.ts
   │  │
   │  ├─ workflow.mapper.ts
   │  ├─ workflow.constants.ts
   │  ├─ workflow.query-keys.ts
   │  │
   │  ├─ use-workflow-page-state.ts
   │  ├─ use-workflow-query.ts
   │  ├─ use-workflow-graph-state.ts
   │  ├─ use-update-workflow.ts
   │  ├─ use-debug-workflow.ts
   │  └─ use-workflow-plugin-registry.ts
   │
   └─ ui/
      ├─ page/
      │  ├─ WorkflowPage.vue
      │  ├─ WorkflowCompositionRoot.vue
      │  ├─ WorkflowPageHeader.vue
      │  ├─ WorkflowPageToolbar.vue
      │  ├─ WorkflowModeSwitcher.vue
      │  └─ WorkflowPageLayout.vue
      │
      ├─ modes/
      │  ├─ WorkflowEditMode.vue
      │  ├─ WorkflowViewMode.vue
      │  └─ WorkflowDebugMode.vue
      │
      ├─ graph/
      │  ├─ WorkflowGraph.vue
      │  ├─ WorkflowGraphCanvas.vue
      │  ├─ WorkflowGraphViewport.vue
      │  ├─ WorkflowGraphControls.vue
      │  ├─ WorkflowGraphMiniMap.vue
      │  ├─ WorkflowGraphBackground.vue
      │  ├─ WorkflowGraphConnectionLine.vue
      │  └─ WorkflowGraphEdge.vue
      │
      ├─ nodes/
      │  ├─ WorkflowNode.vue
      │  ├─ WorkflowNodeHeader.vue
      │  ├─ WorkflowNodeContent.vue
      │  ├─ WorkflowNodeFooter.vue
      │  ├─ WorkflowNodePort.vue
      │  ├─ WorkflowNodeActionGroup.vue
      │  └─ workflow-node-registry.ts
      │
      ├─ plugins/
      │  ├─ WorkflowPluginPanel.vue
      │  ├─ WorkflowPluginList.vue
      │  ├─ WorkflowPluginItem.vue
      │  ├─ WorkflowPluginSlot.vue
      │  └─ workflow-plugin-registry.ts
      │
      ├─ inspector/
      │  ├─ WorkflowInspectorPanel.vue
      │  ├─ WorkflowNodeInspector.vue
      │  ├─ WorkflowEdgeInspector.vue
      │  └─ WorkflowGraphInspector.vue
      │
      ├─ console/
      │  ├─ WorkflowConsole.vue
      │  ├─ WorkflowConsoleCommandInput.vue
      │  └─ WorkflowConsoleOutput.vue
      │
      └─ logs/
         ├─ WorkflowLogPanel.vue
         ├─ WorkflowLogList.vue
         ├─ WorkflowLogItem.vue
         └─ WorkflowLogFilterPanel.vue
```

## Главное дерево зависимости компонентов

```txt
WorkflowPage.vue
└─ WorkflowCompositionRoot.vue
   └─ WorkflowPageLayout.vue
      ├─ WorkflowPageHeader.vue
      ├─ WorkflowPageToolbar.vue
      │  └─ WorkflowModeSwitcher.vue
      │
      └─ modes/
         ├─ WorkflowEditMode.vue
         │  ├─ WorkflowGraph.vue
         │  │  ├─ WorkflowGraphCanvas.vue
         │  │  ├─ WorkflowGraphViewport.vue
         │  │  ├─ WorkflowGraphControls.vue
         │  │  ├─ WorkflowGraphMiniMap.vue
         │  │  ├─ WorkflowGraphBackground.vue
         │  │  ├─ WorkflowGraphConnectionLine.vue
         │  │  ├─ WorkflowGraphEdge.vue
         │  │  └─ WorkflowNode.vue
         │  │     ├─ WorkflowNodeHeader.vue
         │  │     ├─ WorkflowNodeContent.vue
         │  │     ├─ WorkflowNodeFooter.vue
         │  │     ├─ WorkflowNodePort.vue
         │  │     └─ WorkflowNodeActionGroup.vue
         │  │
         │  ├─ WorkflowPluginPanel.vue
         │  │  ├─ WorkflowPluginList.vue
         │  │  ├─ WorkflowPluginItem.vue
         │  │  └─ WorkflowPluginSlot.vue
         │  │
         │  └─ WorkflowInspectorPanel.vue
         │     ├─ WorkflowNodeInspector.vue
         │     ├─ WorkflowEdgeInspector.vue
         │     └─ WorkflowGraphInspector.vue
         │
         ├─ WorkflowViewMode.vue
         │  └─ WorkflowGraph.vue
         │
         └─ WorkflowDebugMode.vue
            ├─ WorkflowGraph.vue
            ├─ WorkflowConsole.vue
            │  ├─ WorkflowConsoleCommandInput.vue
            │  └─ WorkflowConsoleOutput.vue
            │
            └─ WorkflowLogPanel.vue
               ├─ WorkflowLogFilterPanel.vue
               ├─ WorkflowLogList.vue
               └─ WorkflowLogItem.vue
```

## Как разделяются режимы

### `WorkflowEditMode.vue`

Режим редактирования.

В нём доступны:

```txt
Graph
Nodes
Edges
Toolbar actions
Plugin panel
Inspector
Node settings
Edge settings
Graph settings
Save / Update / Delete
```

То есть `EditMode` — самый богатый режим.

```txt
WorkflowEditMode.vue
├─ WorkflowGraph.vue
├─ WorkflowPluginPanel.vue
└─ WorkflowInspectorPanel.vue
```

---

### `WorkflowViewMode.vue`

Режим просмотра.

В нём граф должен быть почти read-only:

```txt
Можно:
- смотреть граф
- открывать детали узлов
- читать настройки

Нельзя:
- двигать узлы
- создавать связи
- удалять элементы
- менять настройки
```

```txt
WorkflowViewMode.vue
└─ WorkflowGraph.vue
```

`WorkflowGraph.vue` тот же самый, но получает режим:

```ts
mode: 'view'
```

И внутри отключает мутации.

---

### `WorkflowDebugMode.vue`

Режим отладки.

В нём главная задача — не редактировать, а смотреть исполнение workflow.

```txt
WorkflowDebugMode.vue
├─ WorkflowGraph.vue
├─ WorkflowConsole.vue
└─ WorkflowLogPanel.vue
```

Здесь граф показывает runtime-состояние:

```txt
Node pending
Node running
Node success
Node failed
Node skipped
```

А справа или снизу находятся:

```txt
Console
Logs
Execution timeline
Node output
Errors
```

## Правильная идея для `WorkflowGraph.vue`

`WorkflowGraph.vue` должен быть универсальным компонентом.

Он не должен знать, где он используется: в Edit, View или Debug.

Он должен получать режим через props:

```ts
type WorkflowMode = 'edit' | 'view' | 'debug';
```

Пример логики:

```ts
const canEdit = computed(() => props.mode === 'edit');
const canDebug = computed(() => props.mode === 'debug');
const readonly = computed(() => props.mode === 'view' || props.mode === 'debug');
```

Тогда один и тот же Graph используется везде:

```txt
EditMode  → WorkflowGraph mode="edit"
ViewMode  → WorkflowGraph mode="view"
DebugMode → WorkflowGraph mode="debug"
```

## Что должно быть в `nodes/`

`nodes/` — это не конкретная бизнес-логика каждого узла, а общий UI-каркас узла.

```txt
nodes/
├─ WorkflowNode.vue
├─ WorkflowNodeHeader.vue
├─ WorkflowNodeContent.vue
├─ WorkflowNodeFooter.vue
├─ WorkflowNodePort.vue
├─ WorkflowNodeActionGroup.vue
└─ workflow-node-registry.ts
```

`WorkflowNode.vue` — универсальная оболочка.

Она может рендерить разные типы узлов через registry:

```ts
workflow-node-registry.ts
```

Пример типов:

```ts
sendMessage
wait
condition
httpRequest
createTask
stack
```

Но сами конкретные реализации узлов лучше потом вынести отдельно, например:

```txt
nodes/node-types/
```

Пока можно не добавлять, если ещё нет конкретных компонентов.

## Что должно быть в `plugins/`

`plugins/` — это расширения редактора.

Например:

```txt
Node Library
Variables
Templates
Validation
History
AI Assistant
Execution Preview
```

Но структура остаётся плоской:

```txt
plugins/
├─ WorkflowPluginPanel.vue
├─ WorkflowPluginList.vue
├─ WorkflowPluginItem.vue
├─ WorkflowPluginSlot.vue
└─ workflow-plugin-registry.ts
```

`WorkflowPluginPanel.vue` — панель.

`WorkflowPluginList.vue` — список доступных плагинов.

`WorkflowPluginItem.vue` — один plugin.

`WorkflowPluginSlot.vue` — место, куда рендерится активный plugin.

`workflow-plugin-registry.ts` — реестр доступных plugin-компонентов.

## Что должно быть в `console/`

`console/` относится именно к Debug-режиму.

```txt
console/
├─ WorkflowConsole.vue
├─ WorkflowConsoleCommandInput.vue
└─ WorkflowConsoleOutput.vue
```

Назначение:

```txt
WorkflowConsole.vue              - контейнер консоли
WorkflowConsoleCommandInput.vue  - ввод команды
WorkflowConsoleOutput.vue        - вывод результата
```

Например:

```txt
run node
show context
show variables
retry failed node
inspect payload
```

## Что должно быть в `logs/`

`logs/` тоже относится к Debug-режиму.

```txt
logs/
├─ WorkflowLogPanel.vue
├─ WorkflowLogList.vue
├─ WorkflowLogItem.vue
└─ WorkflowLogFilterPanel.vue
```

Назначение:

```txt
WorkflowLogPanel.vue        - контейнер логов
WorkflowLogFilterPanel.vue  - фильтр по статусу, node_id, level
WorkflowLogList.vue         - список логов
WorkflowLogItem.vue         - одна запись лога
```

## Главное правило

`Page` не должна знать про `Node`, `Console`, `Log`, `Plugin`, `Inspector`.

Плохо:

```txt
WorkflowPage.vue
├─ WorkflowGraph.vue
├─ WorkflowNode.vue
├─ WorkflowPluginPanel.vue
├─ WorkflowConsole.vue
├─ WorkflowLogPanel.vue
└─ много бизнес-логики
```

Хорошо:

```txt
WorkflowPage.vue
└─ WorkflowCompositionRoot.vue
   └─ WorkflowPageLayout.vue
      └─ WorkflowEditMode.vue / WorkflowViewMode.vue / WorkflowDebugMode.vue
```

То есть страница знает только:

```txt
какой workflow открыт
какой режим активен
какое состояние загрузки
```

А всё остальное уходит ниже.

## Финальная схема ответственности

```txt
WorkflowPage.vue
```

Отвечает за route/page-level.

```txt
WorkflowCompositionRoot.vue
```

Собирает данные, query, mutations, состояние страницы.

```txt
WorkflowPageLayout.vue
```

Раскладывает header, toolbar, workspace.

```txt
WorkflowEditMode.vue
```

Собирает компоненты редактирования.

```txt
WorkflowViewMode.vue
```

Собирает read-only просмотр.

```txt
WorkflowDebugMode.vue
```

Собирает debug-инструменты.

```txt
WorkflowGraph.vue
```

Отвечает за визуализацию графа.

```txt
WorkflowNode.vue
```

Отвечает за внешний вид одного узла.

```txt
WorkflowPluginPanel.vue
```

Отвечает за расширения редактора.

```txt
WorkflowConsole.vue
```

Отвечает за интерактивную debug-консоль.

```txt
WorkflowLogPanel.vue
```

Отвечает за логи выполнения.

## Ключевая идея

Структура должна быть такой:

```txt
workflows/ui/
├─ page/
├─ modes/
├─ graph/
├─ nodes/
├─ plugins/
├─ inspector/
├─ console/
└─ logs/
```

Это достаточно плоско, но при этом каждый тип UI-компонентов находится в своей зоне ответственности. Страница не разрастается, режимы остаются понятными, а Graph, Nodes, Plugins, Console и Logs можно развивать независимо.
