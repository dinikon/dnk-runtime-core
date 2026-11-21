<script setup lang="ts">
import {
  useStatusChangePreview,
  statusChangePreviewSignature,
} from "../model/use-status-change-preview";
import type { StatusChangePreview } from "../model/status-change-preview.types";
import StatusChangePreviewPanel from "../ui/results/StatusChangePreview.vue";
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Button } from "@/components/ui/button";
import { useStatusChangeQuery } from "../model/use-status-change-query";
import StatusChangeExecutionContext from "../ui/forms/StatusChangeExecutionContext.vue";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryUomsQuery } from "../model/use-inventory-item-query";
import {
  useStatusChangePreparation,
  useStatusChangeSourceSnapshots,
  useStatusChangeSources,
} from "../model/use-status-change-posting-queries";
import { usePostStatusChange } from "../model/use-post-status-change";
import { useStatusChangeSourcePicker } from "../model/use-status-change-source-picker";
import { useStatusChangeExecutionDraft } from "../model/use-status-change-execution-draft";
import {
  selectedStatusChangeRows,
  validateStatusChangeExecution,
  hasStatusChangeExecutionErrors,
  StatusChangeExecutionAttempt,
} from "../model/status-change-execution";
import { StatusChangePostingRequestError } from "../model/status-change-posting.errors";
import type {
  StatusChangeAllocation,
  StatusChangeSource,
} from "../model/status-change-posting.types";
import type { InventoryScope } from "../model/inventory-scope.types";
import StatusChangeExecutionForm from "../ui/forms/StatusChangeExecutionForm.vue";
import StatusChangeSourcePickerDialog from "../ui/forms/StatusChangeSourcePickerDialog.vue";
import StatusChangeExecutionStatus from "../ui/forms/StatusChangeExecutionStatus.vue";
import StatusChangeExecutionConfirmDialog from "../ui/forms/StatusChangeExecutionConfirmDialog.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  typeof route.params.documentId === "string" ? route.params.documentId : "",
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const document = useStatusChangeQuery(id, scope);
const query = useStatusChangePreparation(id, scope),
  uoms = useInventoryUomsQuery(scope),
  mutation = usePostStatusChange(scope),
  snapshots = useStatusChangeSourceSnapshots();
const draft = useStatusChangeExecutionDraft(),
  { values, errors, dirty } = draft,
  picker = useStatusChangeSourcePicker(id, scope, identity);
const pending = ref(false),
  refreshing = ref(false),
  conflict = ref(false),
  actualVersion = ref<number | null>(null),
  confirmOpen = ref(false),
  done = ref(false),
  error = ref(""),
  notice = ref("");
const preview = ref<StatusChangePreview | null>(null),
  previewSignature = ref(""),
  previewing = ref(false),
  previewQuery = useStatusChangePreview();
const sourceId = computed(() =>
  typeof route.query.source_position_id === "string"
    ? route.query.source_position_id
    : "",
);
const seedLine = computed(() => values.value?.rows[0]?.documentLineId ?? "");
const seed = useStatusChangeSources(
  id,
  computed(() => ({
    documentLineId: seedLine.value,
    positionId: sourceId.value,
    offset: 0,
    search: "",
  })),
  computed(() => !!sourceId.value && !!seedLine.value),
  scope,
);
const seeded = ref(false);
watch(
  identity,
  () => {
    seeded.value = false;
  },
  { flush: "sync" },
);
watch(
  seed.data,
  (page) => {
    const row = values.value?.rows[0],
      source = page?.items[0];
    if (!row || !source || seeded.value || dirty.value || pending.value) return;
    seeded.value = true;
    draft.change(row.key, { ...row, source, sourceMissing: false });
  },
  { immediate: true },
);
const attempt = reactive(new StatusChangeExecutionAttempt());
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
    previewing.value ||
    attempt.uncertain ||
    conflict.value ||
    !executable.value,
);
const serverVersion = computed(() =>
  Math.max(query.data.value?.version ?? 0, actualVersion.value ?? 0),
);
const selectedCount = computed(() =>
  values.value ? selectedStatusChangeRows(values.value).length : 0,
);
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    draft.reset();
    preview.value = null;
    previewSignature.value = "";
    previewing.value = false;
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
      preview.value = null;
      previewSignature.value = "";
      confirmOpen.value = false;
      actualVersion.value = context.version;
    }
  },
  { immediate: true },
);
function clearErrors(): void {
  preview.value = null;
  previewSignature.value = "";
  confirmOpen.value = false;
  errors.value = { rows: {}, lines: {} };
  error.value = "";
  notice.value = "";
}
function changeRow(key: string, row: StatusChangeAllocation): void {
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
function selectSource(source: StatusChangeSource): void {
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
    previewing.value ||
    attempt.uncertain ||
    !scope.ready.value
  )
    return;
  const captured = identity.value,
    controller = new AbortController(),
    capturedScope: InventoryScope = [...scope.key.value];
  request = controller;
  refreshing.value = true;
  preview.value = null;
  previewSignature.value = "";
  confirmOpen.value = false;
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
    errors.value = validateStatusChangeExecution(values.value);
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
    previewing.value ||
    attempt.uncertain ||
    query.error.value ||
    context.version !== serverVersion.value ||
    !executable.value
  )
    return;
  if (
    !window.confirm(
      "Принять новую версию изменения состояния документа, сохранив количества и исходные позиции? Выполненные строки будут исключены из этого изменения состояния.",
    )
  )
    return;
  draft.accept(context);
  conflict.value = false;
  actualVersion.value = context.version;
  attempt.clear();
  error.value = "";
}
async function submit(): Promise<void> {
  if (
    !values.value ||
    pending.value ||
    !scope.ready.value ||
    (!attempt.uncertain && disabled.value)
  )
    return;
  if (!attempt.uncertain) {
    errors.value = validateStatusChangeExecution(values.value);
    if (hasStatusChangeExecutionErrors(errors.value)) return;
    if (uoms.error.value || !uoms.data.value?.length) {
      error.value = "Повторите загрузку справочника единиц.";
      return;
    }
  }
  if (attempt.uncertain) {
    confirmOpen.value = true;
    return;
  }
  const captured = identity.value,
    signature = statusChangePreviewSignature(values.value),
    controller = new AbortController();
  request = controller;
  previewing.value = true;
  preview.value = null;
  try {
    const result = await previewQuery.calculate(
      id.value,
      values.value,
      [...scope.key.value],
      controller.signal,
    );
    if (
      controller.signal.aborted ||
      captured !== identity.value ||
      !values.value ||
      signature !== statusChangePreviewSignature(values.value)
    )
      return;
    preview.value = result;
    previewSignature.value = signature;
    confirmOpen.value = true;
  } catch (cause: unknown) {
    if (!controller.signal.aborted && captured === identity.value) {
      error.value =
        cause instanceof Error
          ? cause.message
          : "Не удалось проверить изменение состояния.";
      if (cause instanceof StatusChangePostingRequestError) {
        errors.value = cause.fields;
        conflict.value = cause.code === "stock_document_version_conflict";
        actualVersion.value = cause.actualVersion ?? actualVersion.value;
      }
    }
  } finally {
    if (request === controller) {
      request = null;
      previewing.value = false;
    }
  }
}
async function perform(): Promise<void> {
  if (
    !values.value ||
    pending.value ||
    !scope.ready.value ||
    (!attempt.uncertain && disabled.value)
  )
    return;
  if (
    !attempt.uncertain &&
    (!preview.value ||
      previewSignature.value !== statusChangePreviewSignature(values.value))
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
      cause instanceof Error
        ? cause.message
        : "Не удалось провести изменение состояния.";
    if (cause instanceof StatusChangePostingRequestError) {
      errors.value = cause.fields;
      conflict.value = cause.code === "stock_document_version_conflict";
      actualVersion.value = cause.actualVersion ?? actualVersion.value;
      attempt.fail(!cause.status || cause.status >= 500);
    } else attempt.fail(true);
    if (!attempt.uncertain) {
      confirmOpen.value = false;
      preview.value = null;
      previewSignature.value = "";
    }
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
          "Есть несохранённое изменение состояния или неизвестный результат. Покинуть страницу?",
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
    aria-label="Изменение состояния со склада"
  >
    <header class="flex shrink-0 flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Изменить состояние</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Укажите физические источники и фактические количества. Проведение
          перенесёт количество в новое состояние в той же локации.
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
              name: 'inventory-status-change-document',
              params: { documentId: id },
            })
          "
          >К документу</Button
        >
      </div>
    </header>
    <StatusChangeExecutionContext
      :document="document.data.value"
      :loading="document.isPending.value"
      :error="document.error.value?.message ?? ''"
      :disabled="pending || document.isFetching.value || !scope.ready.value"
      @retry="document.refetch()"
    />
    <StatusChangeExecutionStatus
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
      <StatusChangeExecutionForm
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
          pending ||
          previewing ||
          !scope.ready.value ||
          (!attempt.uncertain && disabled)
        "
        >{{
          pending
            ? "Проведение…"
            : attempt.uncertain
              ? "Повторить исходную команду"
              : previewing
                ? "Проверка…"
                : "Проверить изменение состояния"
        }}</Button
      >
    </form>
    <StatusChangeSourcePickerDialog
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
    <StatusChangePreviewPanel v-if="preview" :preview="preview" />
    <StatusChangeExecutionConfirmDialog
      :target-status="query.data.value?.targetStatus ?? ''"
      :preview="preview"
      :reason="query.data.value?.reason ?? ''"
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
