<script setup lang="ts">
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Button } from "@/components/ui/button";
import { useIssueQuery } from "../model/use-issue-query";
import IssueExecutionContext from "../ui/forms/IssueExecutionContext.vue";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryUomsQuery } from "../model/use-inventory-item-query";
import {
  useIssuePreparation,
  useIssueSourceSnapshots,
} from "../model/use-issue-posting-queries";
import { usePostIssue } from "../model/use-post-issue";
import { useIssueSourcePicker } from "../model/use-issue-source-picker";
import { useIssueExecutionDraft } from "../model/use-issue-execution-draft";
import {
  selectedIssueRows,
  validateIssueExecution,
  hasIssueExecutionErrors,
  IssueExecutionAttempt,
} from "../model/issue-execution";
import { IssuePostingRequestError } from "../model/issue-posting.errors";
import type {
  IssueAllocation,
  IssueSource,
} from "../model/issue-posting.types";
import type { InventoryScope } from "../model/inventory-scope.types";
import IssueExecutionForm from "../ui/forms/IssueExecutionForm.vue";
import IssueSourcePickerDialog from "../ui/forms/IssueSourcePickerDialog.vue";
import IssueExecutionStatus from "../ui/forms/IssueExecutionStatus.vue";
import IssueExecutionConfirmDialog from "../ui/forms/IssueExecutionConfirmDialog.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  typeof route.params.documentId === "string" ? route.params.documentId : "",
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const document = useIssueQuery(id, scope);
const query = useIssuePreparation(id, scope),
  uoms = useInventoryUomsQuery(scope),
  mutation = usePostIssue(scope),
  snapshots = useIssueSourceSnapshots();
const draft = useIssueExecutionDraft(),
  { values, errors, dirty } = draft,
  picker = useIssueSourcePicker(id, scope, identity);
const pending = ref(false),
  refreshing = ref(false),
  conflict = ref(false),
  actualVersion = ref<number | null>(null),
  confirmOpen = ref(false),
  done = ref(false),
  error = ref(""),
  notice = ref("");
const attempt = reactive(new IssueExecutionAttempt());
let request: AbortController | null = null;
const executable = computed(() =>
  ["CONFIRMED", "PARTIALLY_EXECUTED"].includes(query.data.value?.status ?? ""),
);
const disabled = computed(
  () =>
    !scope.ready.value ||
    !document.data.value ||
    !!document.error.value ||
    pending.value ||
    refreshing.value ||
    attempt.uncertain ||
    conflict.value ||
    !executable.value,
);
const serverVersion = computed(() =>
  Math.max(query.data.value?.version ?? 0, actualVersion.value ?? 0),
);
const selectedCount = computed(() =>
  values.value ? selectedIssueRows(values.value).length : 0,
);
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    draft.reset();
    pending.value = false;
    refreshing.value = false;
    conflict.value = false;
    actualVersion.value = null;
    confirmOpen.value = false;
    done.value = false;
    error.value = "";
    notice.value = "";
    attempt.clear();
    mutation.reset();
  },
  { flush: "sync" },
);
watch(
  query.data,
  (context) => {
    if (!context || !scope.ready.value || pending.value) return;
    if (!values.value) draft.initialize(context);
    else if (
      context.version !== values.value.expectedVersion &&
      !attempt.uncertain
    ) {
      conflict.value = true;
      actualVersion.value = context.version;
    }
  },
  { immediate: true },
);
function clearErrors(): void {
  errors.value = { rows: {}, lines: {} };
  error.value = "";
  notice.value = "";
}
function changeRow(key: string, row: IssueAllocation): void {
  if (disabled.value) return;
  draft.change(key, row);
  clearErrors();
}
function selectLine(lineId: string, selected: boolean): void {
  if (disabled.value) return;
  draft.select(lineId, selected);
  clearErrors();
}
function split(key: string): void {
  if (disabled.value) return;
  draft.split(key);
  clearErrors();
}
function remove(key: string): void {
  if (disabled.value) return;
  draft.remove(key);
  clearErrors();
}
function openPicker(key: string): void {
  if (disabled.value) return;
  const row = values.value?.rows.find((v) => v.key === key);
  if (row) picker.open(row);
}
function selectSource(source: IssueSource): void {
  const row = values.value?.rows.find((v) => v.key === picker.row.value?.key);
  if (row)
    changeRow(row.key, { ...row, source: { ...source }, sourceMissing: false });
  picker.close();
}
async function refresh(): Promise<void> {
  if (
    !values.value ||
    pending.value ||
    refreshing.value ||
    attempt.uncertain ||
    !scope.ready.value
  )
    return;
  const captured = identity.value,
    controller = new AbortController(),
    capturedScope: InventoryScope = [...scope.key.value];
  request = controller;
  refreshing.value = true;
  error.value = "";
  notice.value = "";
  try {
    const [context, sources] = await Promise.all([
      query.refetch(),
      snapshots.refresh(
        id.value,
        values.value.rows,
        capturedScope,
        controller.signal,
      ),
    ]);
    if (controller.signal.aborted || captured !== identity.value) return;
    if (context.error || !context.data)
      throw context.error ?? new Error("Не удалось обновить документ.");
    draft.updateSources(sources);
    if (context.data.version !== values.value.expectedVersion) {
      conflict.value = true;
      actualVersion.value = context.data.version;
    }
    errors.value = validateIssueExecution(values.value);
    notice.value =
      "Сведения о физическом количестве обновлены. Введённые количества и выбранные позиции сохранены.";
  } catch (cause: unknown) {
    if (!controller.signal.aborted && captured === identity.value)
      error.value =
        cause instanceof Error
          ? cause.message
          : "Не удалось обновить сведения.";
  } finally {
    if (request === controller) {
      request = null;
      refreshing.value = false;
    }
  }
}
function acceptCurrent(): void {
  const context = query.data.value;
  if (
    !context ||
    pending.value ||
    refreshing.value ||
    attempt.uncertain ||
    query.error.value ||
    context.version !== serverVersion.value ||
    !executable.value
  )
    return;
  if (
    !window.confirm(
      "Принять новую версию расходного документа, сохранив количества и исходные позиции? Выполненные строки будут исключены из этой выдачи.",
    )
  )
    return;
  draft.accept(context);
  conflict.value = false;
  actualVersion.value = context.version;
  attempt.clear();
  error.value = "";
}
function submit(): void {
  if (
    !values.value ||
    pending.value ||
    !scope.ready.value ||
    (!attempt.uncertain && disabled.value)
  )
    return;
  if (!attempt.uncertain) {
    errors.value = validateIssueExecution(values.value);
    if (hasIssueExecutionErrors(errors.value)) return;
    if (uoms.error.value || !uoms.data.value?.length) {
      error.value = "Повторите загрузку справочника единиц.";
      return;
    }
  }
  confirmOpen.value = true;
}
async function perform(): Promise<void> {
  if (
    !values.value ||
    pending.value ||
    !scope.ready.value ||
    (!attempt.uncertain && disabled.value)
  )
    return;
  const captured = identity.value,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  error.value = "";
  try {
    const sent = attempt.begin(values.value, () => crypto.randomUUID());
    const result = await mutation.mutateAsync({
      id: id.value,
      values: sent.values,
      key: sent.key,
      scope: [...scope.key.value],
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== identity.value) return;
    done.value = true;
    attempt.clear();
    confirmOpen.value = false;
    void router.replace({
      name: "inventory-stock-execution",
      params: { identifier: result.executionId },
    });
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    error.value =
      cause instanceof Error ? cause.message : "Не удалось провести расход.";
    if (cause instanceof IssuePostingRequestError) {
      errors.value = cause.fields;
      conflict.value = cause.code === "stock_document_version_conflict";
      actualVersion.value = cause.actualVersion ?? actualVersion.value;
      attempt.fail(!cause.status || cause.status >= 500);
    } else attempt.fail(true);
    if (!attempt.uncertain) confirmOpen.value = false;
    if (conflict.value) await query.refetch();
  } finally {
    if (request === controller) {
      request = null;
      pending.value = false;
    }
  }
}
function canLeave(): boolean {
  return (
    done.value ||
    (!pending.value &&
      (!(dirty.value || attempt.uncertain) ||
        window.confirm(
          "Есть несохранённый расход или неизвестный результат. Покинуть страницу?",
        )))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) => to.params.documentId === from.params.documentId || canLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (!done.value && (dirty.value || pending.value || attempt.uncertain)) {
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
    aria-label="Выдача со склада"
  >
    <header class="flex shrink-0 flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Выдать товар</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Укажите физические источники и фактические количества. Проведение
          уменьшит запас выбранных позиций.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          variant="outline"
          :disabled="
            pending || refreshing || attempt.uncertain || !scope.ready.value
          "
          @click="refresh"
          >{{ refreshing ? "Обновление…" : "Обновить сведения" }}</Button
        ><Button
          variant="outline"
          :disabled="pending"
          @click="
            router.push({
              name: 'inventory-issue-document',
              params: { documentId: id },
            })
          "
          >К документу</Button
        >
      </div>
    </header>
    <IssueExecutionContext
      :document="document.data.value"
      :loading="document.isPending.value"
      :error="document.error.value?.message ?? ''"
      :disabled="pending || document.isFetching.value || !scope.ready.value"
      @retry="document.refetch()"
    />
    <IssueExecutionStatus
      :loading="query.isPending.value"
      :error="scope.error.value || query.error.value?.message || ''"
      :executable="executable"
      :has-draft="!!values"
      :conflict="conflict"
      :uncertain="attempt.uncertain"
      :expected-version="values?.expectedVersion ?? 0"
      :server-version="serverVersion"
      :refresh-disabled="
        pending ||
        refreshing ||
        query.isFetching.value ||
        !scope.ready.value ||
        attempt.uncertain
      "
      :accept-disabled="
        pending ||
        refreshing ||
        !!query.error.value ||
        query.data.value?.version !== serverVersion ||
        !executable
      "
      @retry="refresh"
      @accept="acceptCurrent"
    />
    <form
      v-if="values && scope.ready.value"
      class="flex w-full max-w-5xl shrink-0 flex-col gap-4 rounded-lg border bg-card p-4 sm:p-6"
      @submit.prevent="submit"
    >
      <p class="text-sm text-muted-foreground">
        Основание формы: версия {{ values.expectedVersion }}. Показано
        физическое количество без расчёта коммерческой доступности.
      </p>
      <p v-if="notice" role="status" class="text-sm text-muted-foreground">
        {{ notice }}
      </p>
      <IssueExecutionForm
        :values="values"
        :context="query.data.value"
        :errors="errors"
        :disabled="disabled"
        :uoms="uoms.data.value ?? []"
        :uom-error="uoms.error.value?.message ?? ''"
        @change="changeRow"
        @select="selectLine"
        @split="split"
        @remove="remove"
        @pick="openPicker"
        @retry-units="uoms.refetch()"
      />
      <p
        v-if="error"
        role="alert"
        class="rounded-md border border-destructive p-3 text-sm text-destructive"
      >
        {{ error
        }}<Button
          type="button"
          variant="outline"
          :disabled="pending || refreshing || attempt.uncertain"
          @click="refresh"
          >Обновить физическое количество</Button
        >
      </p>
      <Button
        type="submit"
        class="self-start"
        :disabled="
          pending || !scope.ready.value || (!attempt.uncertain && disabled)
        "
        >{{
          pending
            ? "Проведение…"
            : attempt.uncertain
              ? "Повторить исходную команду"
              : "Проверить и выдать"
        }}</Button
      >
    </form>
    <IssueSourcePickerDialog
      v-if="picker.row.value"
      :search="picker.search.value"
      :items="picker.items.value"
      :loading="picker.loading.value"
      :error="picker.error.value"
      :offset="picker.offset.value"
      :total="picker.total.value"
      @close="picker.close"
      @search="picker.setSearch"
      @select="selectSource"
      @page="picker.page"
      @retry="picker.retry"
    />
    <IssueExecutionConfirmDialog
      v-if="confirmOpen && values"
      :version="values.expectedVersion"
      :count="selectedCount"
      :pending="pending"
      :uncertain="attempt.uncertain"
      :error="error"
      @close="!pending && (confirmOpen = false)"
      @confirm="perform"
    />
  </section>
</template>
