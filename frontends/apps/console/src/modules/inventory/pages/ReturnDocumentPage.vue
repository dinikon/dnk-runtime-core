<script setup lang="ts">
import ReturnReasonField from "../ui/forms/ReturnReasonField.vue";
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useReturnQuery } from "../model/use-return-query";
import { useUpdateReturn } from "../model/use-update-return";
import { useConfirmReturn } from "../model/use-confirm-return";
import { useCancelReturn } from "../model/use-cancel-return";
import { useInventoryUomsQuery } from "../model/use-inventory-item-query";
import {
  returnEditValues,
  returnEditSignature,
  copyReturnEdit,
  validateReturnEdit,
  replaceReturnLine,
} from "../model/return-edit";
import { hasReturnErrors } from "../model/return-draft";
import { ReturnRequestError } from "../model/return.errors";
import type {
  ReturnDocument,
  ReturnDraftLine,
  ReturnEditValues,
  ReturnErrors,
} from "../model/return.types";
import type { InventoryScope } from "../model/inventory-scope.types";
import { useReturnExecutionHistory } from "../model/use-return-posting-queries";
import ReturnExecutionHistory from "../ui/results/ReturnExecutionHistory.vue";
import ReturnDocumentDetails from "../ui/results/ReturnDocumentDetails.vue";
import ReturnPlanLinesForm from "../ui/forms/ReturnPlanLinesForm.vue";
import { useReturnOrigin } from "../model/use-return-origin";
import { toggleReturnOrigin } from "../model/return-plan";
import type { ReturnOriginLine } from "../model/return-origin.types";
import ReturnDocumentActionDialog from "../ui/forms/ReturnDocumentActionDialog.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  typeof route.params.documentId === "string" ? route.params.documentId : "",
);
const query = useReturnQuery(id, scope),
  update = useUpdateReturn(scope),
  confirm = useConfirmReturn(scope),
  cancel = useCancelReturn(scope);
const historyOffset = computed(() =>
  Math.max(
    0,
    Number.parseInt(
      typeof route.query.executions_offset === "string"
        ? route.query.executions_offset
        : "0",
      10,
    ) || 0,
  ),
);
const history = useReturnExecutionHistory(id, historyOffset, scope);
function historyPage(offset: number): void {
  void router.replace({
    query: {
      ...route.query,
      executions_offset: offset ? String(offset) : undefined,
    },
  });
}
watch(
  () => history.data.value,
  (page) => {
    if (page && page.offset >= page.total && page.offset > 0)
      historyPage(
        Math.max(0, Math.floor((page.total - 1) / page.limit) * page.limit),
      );
  },
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const editor = ref<ReturnEditValues | null>(null),
  baseline = ref(""),
  notice = ref(""),
  error = ref(""),
  errors = ref<ReturnErrors>({ lineFields: {} });
const pending = ref(false),
  conflict = ref(false),
  uncertain = ref(false);
const action = ref<"confirm" | "cancel" | null>(null),
  actionVersion = ref(0);
const observedVersion = ref<number | null>(null);
const serverVersion = computed(() =>
  Math.max(query.data.value?.version ?? 0, observedVersion.value ?? 0),
);
const uoms = useInventoryUomsQuery(scope);
const origin = useReturnOrigin(
  computed(() => query.data.value?.originExecutionId ?? ""),
  scope,
);
const dirty = computed(
  () => !!editor.value && returnEditSignature(editor.value) !== baseline.value,
);
const manual = computed(() => query.data.value?.sourceSystem === null);
const editable = computed(
  () => manual.value && query.data.value?.status === "DRAFT",
);
const cancellable = computed(
  () =>
    manual.value &&
    ["DRAFT", "CONFIRMED"].includes(query.data.value?.status ?? "") &&
    query.data.value?.lines.every((line) =>
      /^0(?:\.0+)?$/.test(line.executedQty),
    ),
);
const disabled = computed(
  () =>
    pending.value ||
    conflict.value ||
    uncertain.value ||
    !scope.ready.value ||
    !editable.value,
);
const actionsDisabled = computed(
  () =>
    pending.value ||
    uncertain.value ||
    conflict.value ||
    dirty.value ||
    query.data.value?.version !== serverVersion.value ||
    !scope.ready.value,
);
let request: AbortController | null = null;
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    editor.value = null;
    baseline.value = "";
    notice.value = "";
    error.value = "";
    errors.value = { lineFields: {} };
    pending.value = false;
    conflict.value = false;
    uncertain.value = false;
    action.value = null;
    observedVersion.value = null;
    update.reset();
    confirm.reset();
    cancel.reset();
  },
  { flush: "sync" },
);
watch(query.data, (document) => {
  if (!document || pending.value) return;
  if (
    (editor.value && document.version !== editor.value.expectedVersion) ||
    (action.value && document.version !== actionVersion.value)
  ) {
    conflict.value = true;
    error.value =
      "Документ изменён. Локальный черновик сохранён; проверьте актуальный план.";
  }
});
function clearErrors(): void {
  errors.value = { lineFields: {} };
  error.value = "";
  notice.value = "";
}
function edit(): void {
  const document = query.data.value;
  if (!document || !editable.value || actionsDisabled.value) return;
  editor.value = returnEditValues(document);
  baseline.value = returnEditSignature(editor.value);
  clearErrors();
}
function discard(): void {
  if (
    pending.value ||
    (dirty.value && !window.confirm("Отбросить несохранённые изменения строк?"))
  )
    return;
  editor.value = null;
  baseline.value = "";
  conflict.value = false;
  errors.value = { lineFields: {} };
}
function acceptCurrent(): void {
  const document = query.data.value;
  if (
    !document ||
    pending.value ||
    uncertain.value ||
    query.error.value ||
    document.version !== serverVersion.value
  )
    return;
  if (
    dirty.value &&
    !window.confirm(
      "Заменить локальный черновик актуальным планом? Несохранённые изменения будут потеряны.",
    )
  )
    return;
  editor.value =
    document.status === "DRAFT" && document.sourceSystem === null
      ? returnEditValues(document)
      : null;
  baseline.value = editor.value ? returnEditSignature(editor.value) : "";
  conflict.value = false;
  action.value = null;
  clearErrors();
}
function changeLine(key: string, line: ReturnDraftLine): void {
  if (!editor.value || disabled.value) return;
  editor.value = replaceReturnLine(editor.value, key, line);
  clearErrors();
}
function selectOrigin(line: ReturnOriginLine, selected: boolean): void {
  if (!editor.value || disabled.value) return;
  editor.value.lines = toggleReturnOrigin(
    editor.value.lines,
    line,
    selected,
    () => crypto.randomUUID(),
  );
  clearErrors();
}
function openAction(value: "confirm" | "cancel"): void {
  const document = query.data.value;
  if (!document || actionsDisabled.value) return;
  if (value === "confirm" && (!editable.value || !document.lines.length))
    return;
  if (value === "cancel" && !cancellable.value) return;
  clearErrors();
  actionVersion.value = document.version;
  action.value = value;
}
async function perform(kind: "update" | "confirm" | "cancel"): Promise<void> {
  if (pending.value || uncertain.value || conflict.value || !scope.ready.value)
    return;
  if (kind === "update") {
    if (!editor.value || !editable.value || !dirty.value) return;
    errors.value = validateReturnEdit(editor.value);
    if (hasReturnErrors(errors.value)) return;
    if (
      editor.value.lines.length &&
      (!uoms.data.value?.length || uoms.error.value)
    ) {
      error.value = "Повторите загрузку справочника единиц.";
      return;
    }
  } else if (dirty.value || action.value !== kind) return;
  const captured = identity.value,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  error.value = "";
  notice.value = "";
  try {
    const scopeSnapshot: InventoryScope = [...scope.key.value];
    const common = {
      id: id.value,
      scope: scopeSnapshot,
      signal: controller.signal,
    };
    let result: ReturnDocument;
    if (kind === "update" && editor.value)
      result = await update.mutateAsync({
        ...common,
        values: copyReturnEdit(editor.value),
      });
    else if (kind === "confirm")
      result = await confirm.mutateAsync({
        ...common,
        values: { expectedVersion: actionVersion.value },
      });
    else if (kind === "cancel")
      result = await cancel.mutateAsync({
        ...common,
        values: { expectedVersion: actionVersion.value },
      });
    else return;
    if (controller.signal.aborted || captured !== identity.value) return;
    if (kind === "update") {
      editor.value = returnEditValues(result);
      baseline.value = returnEditSignature(editor.value);
    } else {
      editor.value = null;
      baseline.value = "";
      action.value = null;
    }
    conflict.value = false;
    observedVersion.value = result.version;
    if ((query.data.value?.version ?? result.version) > result.version) {
      conflict.value = true;
      error.value =
        "Документ уже изменён после сохранения. Проверьте актуальный план.";
    }
    errors.value = { lineFields: {} };
    notice.value =
      kind === "update"
        ? "Изменения плана сохранены."
        : kind === "confirm"
          ? "План подтверждён. Физические остатки не изменены."
          : "Документ отменён.";
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    error.value =
      cause instanceof Error ? cause.message : "Не удалось выполнить действие.";
    if (cause instanceof ReturnRequestError) {
      errors.value = cause.fields;
      conflict.value = cause.status === 409;
      observedVersion.value =
        cause.conflict?.actualVersion ?? observedVersion.value;
      uncertain.value = !cause.status || cause.status >= 500;
    } else uncertain.value = true;
    if (conflict.value) await query.refetch();
  } finally {
    if (request === controller) {
      request = null;
      pending.value = false;
    }
  }
}
async function checkState(): Promise<void> {
  if (pending.value || !scope.ready.value) return;
  const captured = identity.value;
  pending.value = true;
  try {
    const result = await query.refetch();
    if (captured !== identity.value) return;
    if (result.error || !result.data) {
      error.value = result.error?.message ?? "Не удалось проверить состояние.";
      return;
    }
    uncertain.value = false;
    observedVersion.value = result.data.version;
    action.value = null;
    conflict.value =
      !!editor.value && editor.value.expectedVersion !== result.data.version;
    error.value = conflict.value
      ? "Серверная версия изменилась. Локальный черновик сохранён."
      : "";
    notice.value =
      "Показано актуальное состояние документа. Повтор действия выполняется только вручную.";
  } finally {
    if (captured === identity.value) pending.value = false;
  }
}
function back(): void {
  const path = route.query.returnTo;
  void router.push(
    typeof path === "string" &&
      /^\/inventory\/stock-documents\/returns(?:\?|$)/.test(path)
      ? path
      : { name: "inventory-return-documents" },
  );
}
async function copy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(id.value);
    notice.value = "Идентификатор скопирован.";
  } catch {
    notice.value =
      "Не удалось скопировать. Идентификатор можно выделить вручную.";
  }
}
function canLeave(): boolean {
  return (
    !pending.value &&
    (!dirty.value ||
      window.confirm("Есть несохранённые изменения плана. Покинуть страницу?"))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) => to.params.documentId === from.params.documentId || canLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (dirty.value || pending.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => {
  request?.abort();
  window.removeEventListener("beforeunload", beforeUnload);
});
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Карточка возврата"
  >
    <header class="flex shrink-0 flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <h1 class="text-2xl font-semibold">Возврат</h1>
        <p class="mt-1 break-all font-mono text-xs text-muted-foreground">
          {{ id }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button variant="outline" :disabled="pending" @click="back"
          >К списку</Button
        ><Button
          variant="outline"
          :disabled="!query.data.value || !scope.ready.value"
          @click="copy"
          >Копировать ID</Button
        ><Button
          variant="outline"
          :disabled="!scope.ready.value || query.isFetching.value || pending"
          @click="query.refetch()"
          >Обновить</Button
        >
      </div>
    </header>
    <div
      v-if="query.data.value && scope.ready.value"
      class="flex shrink-0 flex-wrap items-center gap-2"
    >
      <Button
        v-if="
          manual &&
          ['CONFIRMED', 'PARTIALLY_EXECUTED'].includes(
            query.data.value?.status ?? '',
          )
        "
        :disabled="actionsDisabled"
        @click="
          router.push({
            name: 'inventory-return-execute',
            params: { documentId: id },
            query: {
              source_position_id:
                typeof route.query.source_position_id === 'string'
                  ? route.query.source_position_id
                  : undefined,
            },
          })
        "
        >{{
          query.data.value.status === "PARTIALLY_EXECUTED"
            ? "Провести возврат остатка"
            : "Провести возврат"
        }}</Button
      >
      <Button
        v-if="editable && !editor"
        variant="outline"
        :disabled="actionsDisabled"
        @click="edit"
        >Редактировать черновик</Button
      >
      <Button
        v-if="editable"
        :disabled="actionsDisabled || !query.data.value.lines.length"
        @click="openAction('confirm')"
        >Подтвердить</Button
      >
      <Button
        v-if="cancellable"
        variant="destructive"
        :disabled="actionsDisabled"
        @click="openAction('cancel')"
        >Отменить документ</Button
      >
      <p v-if="dirty" class="text-sm text-muted-foreground">
        Перед подтверждением или отменой сохраните изменения либо завершите
        редактирование.
      </p>
    </div>
    <p
      v-if="notice"
      role="status"
      class="shrink-0 text-sm text-muted-foreground"
    >
      {{ notice }}
    </p>
    <div
      v-if="scope.error.value || query.error.value"
      role="alert"
      class="shrink-0 rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ scope.error.value || query.error.value?.message
      }}<Button
        variant="outline"
        :disabled="!scope.ready.value || query.isFetching.value || pending"
        @click="query.refetch()"
        >Повторить</Button
      >
    </div>
    <div
      v-if="error && !action"
      role="alert"
      class="shrink-0 rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ error }}
    </div>
    <div
      v-if="uncertain"
      role="alert"
      class="shrink-0 rounded-md bg-muted p-3 text-sm"
    >
      Результат действия неизвестен. Проверьте состояние перед повтором;
      введённые изменения сохранены.<Button
        variant="outline"
        :disabled="pending"
        @click="checkState"
        >Проверить состояние</Button
      >
    </div>
    <div
      v-if="conflict"
      role="alert"
      class="shrink-0 rounded-md bg-muted p-3 text-sm"
    >
      Конфликт версии. Локальный план:
      {{ editor?.expectedVersion ?? actionVersion }}, серверный:
      {{ serverVersion }}. Автоматическое объединение не выполняется.
      <Button
        variant="outline"
        :disabled="pending || query.isFetching.value"
        @click="query.refetch()"
        >Загрузить актуальный план</Button
      >
      <Button
        variant="outline"
        :disabled="
          pending ||
          uncertain ||
          !query.data.value ||
          !!query.error.value ||
          query.data.value.version !== serverVersion
        "
        @click="acceptCurrent"
        >Принять актуальный план</Button
      >
    </div>
    <p v-if="query.isPending.value" role="status">Загрузка возврата…</p>
    <p
      v-else-if="query.isFetching.value"
      role="status"
      class="text-xs text-muted-foreground"
    >
      Обновление…
    </p>
    <form
      v-if="editor && scope.ready.value"
      class="flex w-full max-w-5xl shrink-0 flex-col gap-4 rounded-lg border bg-card p-4 sm:p-6"
      aria-label="Редактор плана возврата"
      @submit.prevent="perform('update')"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-lg font-semibold">
          Редактирование плана · версия {{ editor.expectedVersion }}
        </h2>
        <Button
          type="button"
          variant="outline"
          :disabled="pending"
          @click="discard"
          >Завершить редактирование</Button
        >
      </div>
      <p v-if="!editable" class="text-sm text-muted-foreground">
        План больше нельзя редактировать. Несохранённый ввод оставлен для
        сверки.
      </p>
      <p v-if="uoms.error.value" role="alert" class="text-sm text-destructive">
        {{ uoms.error.value.message
        }}<Button
          type="button"
          variant="outline"
          :disabled="pending || uoms.isFetching.value"
          @click="uoms.refetch()"
          >Повторить загрузку единиц</Button
        >
      </p>
      <ReturnReasonField
        :value="editor.reason"
        :error="errors.reason"
        :disabled="pending || conflict || uncertain || !scope.ready.value"
        @change="
          editor.reason = $event;
          clearErrors();
        "
      />
      <p v-if="origin.error.value" role="alert">
        {{ origin.error.value.message
        }}<Button type="button" variant="outline" @click="origin.refetch()"
          >Обновить основание</Button
        >
      </p>
      <ReturnPlanLinesForm
        :origins="origin.data.value?.lines ?? []"
        :lines="editor.lines"
        :errors="errors"
        :disabled="disabled || !origin.data.value || !!origin.error.value"
        :uoms="uoms.data.value ?? []"
        @change="changeLine"
        @select="selectOrigin"
      />
      <Button type="submit" class="self-start" :disabled="disabled || !dirty">{{
        pending ? "Сохранение…" : "Сохранить изменения"
      }}</Button>
    </form>
    <Button
      v-if="query.data.value"
      class="self-start"
      variant="outline"
      @click="
        router.push({
          name: 'inventory-stock-execution',
          params: { identifier: query.data.value.originExecutionId },
        })
      "
      >Исходное исполнение</Button
    >
    <ReturnDocumentDetails
      v-if="query.data.value && scope.ready.value"
      :document="query.data.value"
    />
    <ReturnExecutionHistory
      v-if="scope.ready.value && query.data.value"
      :page="history.data.value"
      :loading="history.isPending.value"
      :pending="history.isFetching.value"
      :error="history.error.value?.message ?? ''"
      @retry="history.refetch()"
      @open="
        router.push({
          name: 'inventory-stock-execution',
          params: { identifier: $event },
        })
      "
      @posting="
        router.push({
          name: 'inventory-stock-posting',
          params: { identifier: $event },
        })
      "
      @page="historyPage"
    />
    <ReturnDocumentActionDialog
      :direction="query.data.value?.direction ?? ''"
      :reason="query.data.value?.reason ?? ''"
      v-if="action"
      :action="action"
      :version="actionVersion"
      :pending="pending"
      :error="error"
      :blocked="conflict || uncertain"
      @close="!pending && (action = null)"
      @confirm="perform(action)"
      @check="checkState"
    />
  </section>
</template>
