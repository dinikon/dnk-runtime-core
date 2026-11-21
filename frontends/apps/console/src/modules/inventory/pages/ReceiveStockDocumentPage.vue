<script setup lang="ts">
import { computed, ref, reactive, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryUomsQuery } from "../model/use-inventory-item-query";
import { useReceiptPreparation } from "../model/use-receipt-posting-queries";
import { usePostReceipt } from "../model/use-post-receipt";
import { useReceiptReferencePicker } from "../model/use-receipt-reference-picker";
import {
  copyIntake,
  chooseIntakeReference,
  validateIntake,
  ReceiptIntakeAttempt,
  intakeGroups,
  selectedIntakeRows,
} from "../model/receipt-intake";
import { ReceiptPostingRequestError } from "../model/receipt-posting.errors";
import type {
  IntakeRow,
  IntakeUnallocatedCost,
  IntakeReference,
  ReceiptReferenceKind,
} from "../model/receipt-posting.types";
import type { InventoryScope } from "../model/inventory-scope.types";
import ReceiptIntakeCostForm from "../ui/forms/ReceiptIntakeCostForm.vue";
import ReceiptIntakePlanForm from "../ui/forms/ReceiptIntakePlanForm.vue";
import ReceiptIntakeStatus from "../ui/forms/ReceiptIntakeStatus.vue";
import { useReceiptIntakeDraft } from "../model/use-receipt-intake-draft";
import ReceiptIntakePickerDialog from "../ui/forms/ReceiptIntakePickerDialog.vue";
import ReceiptIntakeConfirmDialog from "../ui/forms/ReceiptIntakeConfirmDialog.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  typeof route.params.documentId === "string" ? route.params.documentId : "",
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const query = useReceiptPreparation(id, scope),
  uoms = useInventoryUomsQuery(scope),
  mutation = usePostReceipt(scope),
  picker = useReceiptReferencePicker(id, scope, identity);
const draft = useReceiptIntakeDraft();
const { values, errors, dirty } = draft;
const groups = computed(() =>
  values.value ? intakeGroups(values.value, query.data.value) : [],
);
const selectedCount = computed(() =>
  values.value ? selectedIntakeRows(values.value).length : 0,
);
const error = ref(""),
  pending = ref(false),
  conflict = ref(false),
  actualVersion = ref<number | null>(null),
  confirmOpen = ref(false),
  done = ref(false),
  attempt = reactive(new ReceiptIntakeAttempt());
let request: AbortController | null = null;
const receivable = computed(() =>
  ["CONFIRMED", "PARTIALLY_EXECUTED"].includes(query.data.value?.status ?? ""),
);
const disabled = computed(
  () =>
    !scope.ready.value ||
    pending.value ||
    attempt.uncertain ||
    conflict.value ||
    !receivable.value,
);
const serverVersion = computed(() =>
  Math.max(query.data.value?.version ?? 0, actualVersion.value ?? 0),
);
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    draft.reset();
    error.value = "";
    pending.value = false;
    conflict.value = false;
    actualVersion.value = null;
    confirmOpen.value = false;
    done.value = false;
    attempt.clear();
    mutation.reset();
  },
  { flush: "sync" },
);
watch(
  query.data,
  (context) => {
    if (!context || !scope.ready.value || pending.value) return;
    if (!values.value) {
      draft.initialize(context);
    } else if (
      context.version !== values.value.expectedVersion &&
      !attempt.uncertain
    ) {
      conflict.value = true;
      actualVersion.value = context.version;
    }
  },
  { immediate: true },
);
function clearError(): void {
  error.value = "";
  errors.value = { rows: {} };
}
function changeRow(key: string, row: IntakeRow): void {
  if (!values.value || disabled.value) return;
  draft.change(key, row);
  clearError();
}
function changeCost(value: IntakeUnallocatedCost): void {
  if (!values.value || disabled.value) return;
  values.value.unallocatedCost = { ...value };
  clearError();
}
function removeRow(key: string): void {
  if (!values.value || disabled.value) return;
  draft.remove(key);
  clearError();
}
function splitRow(key: string): void {
  if (!values.value || disabled.value || selectedCount.value >= 500) return;
  draft.split(key);
  clearError();
}
function openPicker(key: string, kind: ReceiptReferenceKind): void {
  if (disabled.value) return;
  const row = values.value?.rows.find((value) => value.key === key);
  if (row) picker.open(row, kind);
}
function selectReference(option: IntakeReference): void {
  const selected = picker.selection.value,
    row = values.value?.rows.find((value) => value.key === selected?.key);
  if (selected && row)
    changeRow(row.key, chooseIntakeReference(row, selected.kind, option));
  picker.close();
}
function selectLine(id: string, selected: boolean): void {
  if (disabled.value) return;
  draft.select(id, selected);
  clearError();
}
function fillLine(lineId: string): void {
  const context = query.data.value;
  if (!context || disabled.value) return;
  if (
    !window.confirm(
      "Заполнить строку оставшимся количеством? Введённые распределения этой строки будут заменены.",
    )
  )
    return;
  draft.fill(context, lineId);
  clearError();
}
function acceptCurrent(): void {
  const context = query.data.value;
  if (
    !context ||
    pending.value ||
    attempt.uncertain ||
    query.error.value ||
    context.version !== serverVersion.value ||
    !receivable.value
  )
    return;
  if (
    !window.confirm(
      "Принять новую версию документа, сохранив введённые количества и распределения? Полностью выполненные строки будут исключены из текущей приёмки.",
    )
  )
    return;
  draft.accept(context);
  actualVersion.value = context.version;
  conflict.value = false;
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
    errors.value = validateIntake(values.value);
    if (
      errors.value.form ||
      errors.value.costs ||
      Object.keys(errors.value.lines ?? {}).length ||
      Object.keys(errors.value.rows).length
    )
      return;
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
    const sent = attempt.begin(copyIntake(values.value), () =>
        crypto.randomUUID(),
      ),
      capturedScope: InventoryScope = [...scope.key.value];
    const result = await mutation.mutateAsync({
      id: id.value,
      values: sent.values,
      key: sent.key,
      scope: capturedScope,
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
      cause instanceof Error ? cause.message : "Не удалось провести приёмку.";
    if (cause instanceof ReceiptPostingRequestError) {
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
          "Есть несохранённый факт или неизвестный результат приёмки. Покинуть страницу?",
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
    aria-label="Приёмка поступления"
  >
    <header class="flex shrink-0 flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Принять товар</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Укажите фактически принятое количество. После подтверждения товар
          появится в остатках склада.
        </p>
      </div>
      <Button
        variant="outline"
        :disabled="pending"
        @click="
          router.push({
            name: 'inventory-receipt-document',
            params: { documentId: id },
          })
        "
        >К документу</Button
      >
    </header>
    <ReceiptIntakeStatus
      :loading="query.isPending.value"
      :error="scope.error.value || query.error.value?.message || ''"
      :receivable="receivable"
      :has-draft="!!values"
      :conflict="conflict"
      :uncertain="attempt.uncertain"
      :expected-version="values?.expectedVersion ?? 0"
      :server-version="serverVersion"
      :refresh-disabled="
        pending || query.isFetching.value || !scope.ready.value
      "
      :accept-disabled="
        pending ||
        query.isFetching.value ||
        !!query.error.value ||
        query.data.value?.version !== serverVersion ||
        !receivable
      "
      @retry="query.refetch()"
      @accept="acceptCurrent"
    />
    <div
      v-if="values && scope.ready.value"
      class="flex w-full max-w-5xl shrink-0 flex-col gap-5"
    >
      <p class="text-sm text-muted-foreground">
        Основание формы: версия {{ values.expectedVersion }}. Для серийного
        учёта каждый экземпляр принимается отдельно в количестве 1 PCS.
      </p>
      <form
        class="flex shrink-0 flex-col gap-5 rounded-lg border bg-card p-4 sm:p-6"
        @submit.prevent="submit"
      >
        <ReceiptIntakePlanForm
          :groups="groups"
          :row-count="selectedCount"
          @select="selectLine"
          @fill="fillLine"
          :disabled="disabled"
          :errors="errors"
          :uoms="uoms.data.value ?? []"
          :uom-error="uoms.error.value?.message ?? ''"
          :uom-pending="pending || uoms.isFetching.value"
          @retry-units="uoms.refetch()"
          @change="changeRow"
          @remove="removeRow"
          @split="splitRow"
          @pick="openPicker"
        />
        <ReceiptIntakeCostForm
          :value="values.unallocatedCost"
          :disabled="disabled"
          :error="errors.costs ?? ''"
          @change="changeCost"
        />
        <p
          v-if="error"
          role="alert"
          class="rounded-md border border-destructive p-3 text-sm text-destructive"
        >
          {{ error }}
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
                : "Проверить и принять"
          }}</Button
        >
      </form>
    </div>
    <ReceiptIntakePickerDialog
      v-if="picker.selection.value"
      :kind="picker.selection.value.kind"
      :search="picker.search.value"
      :items="picker.items.value"
      :loading="picker.loading.value"
      :error="picker.error.value"
      :offset="picker.offset.value"
      :total="picker.total.value"
      @close="picker.close"
      @search="picker.setSearch"
      @select="selectReference"
      @page="picker.page"
      @retry="picker.retry"
    />
    <ReceiptIntakeConfirmDialog
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
