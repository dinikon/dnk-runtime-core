<script setup lang="ts">
import { computed, ref, reactive, watch, onBeforeUnmount } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryUomsQuery } from "../model/use-inventory-item-query";
import { useReceiptPreparation } from "../model/use-receipt-posting-queries";
import { usePostReceipt } from "../model/use-post-receipt";
import { useReceiptReferencePicker } from "../model/use-receipt-reference-picker";
import {
  prepareIntake,
  copyIntake,
  intakeSignature,
  duplicateIntakeRow,
  chooseIntakeReference,
  validateIntake,
  ReceiptIntakeAttempt,
} from "../model/receipt-intake";
import { ReceiptPostingRequestError } from "../model/receipt-posting.errors";
import type {
  ReceiptIntakeValues,
  ReceiptIntakeErrors,
  IntakeRow,
  IntakeReference,
  ReceiptReferenceKind,
} from "../model/receipt-posting.types";
import type { InventoryScope } from "../model/inventory-scope.types";
import ReceiptIntakeLinesForm from "../ui/forms/ReceiptIntakeLinesForm.vue";
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
const values = ref<ReceiptIntakeValues | null>(null),
  baseline = ref(""),
  errors = ref<ReceiptIntakeErrors>({ rows: {} }),
  error = ref(""),
  pending = ref(false),
  conflict = ref(false),
  actualVersion = ref<number | null>(null),
  confirmOpen = ref(false),
  done = ref(false),
  attempt = reactive(new ReceiptIntakeAttempt());
let request: AbortController | null = null;
const dirty = computed(
  () => !!values.value && intakeSignature(values.value) !== baseline.value,
);
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
    values.value = null;
    baseline.value = "";
    errors.value = { rows: {} };
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
      values.value = prepareIntake(context, () => crypto.randomUUID());
      baseline.value = intakeSignature(values.value);
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
  values.value.rows = values.value.rows.map((value) =>
    value.key === key ? { ...row, key: value.key } : value,
  );
  clearError();
}
function removeRow(key: string): void {
  if (!values.value || disabled.value) return;
  values.value.rows = values.value.rows.filter((row) => row.key !== key);
  clearError();
}
function splitRow(key: string): void {
  if (!values.value || disabled.value || values.value.rows.length >= 500)
    return;
  const row = values.value.rows.find((value) => value.key === key);
  if (row) values.value.rows.push(duplicateIntakeRow(row, crypto.randomUUID()));
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
function replacePlan(): void {
  const context = query.data.value;
  if (
    !context ||
    pending.value ||
    attempt.uncertain ||
    query.error.value ||
    context.version !== serverVersion.value
  )
    return;
  if (
    dirty.value &&
    !window.confirm(
      "Заменить введённый факт актуальным остатком плана? Несохранённый ввод будет потерян.",
    )
  )
    return;
  values.value = prepareIntake(context, () => crypto.randomUUID());
  baseline.value = intakeSignature(values.value);
  conflict.value = false;
  attempt.clear();
  clearError();
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
          Фактическое исполнение и физический остаток фиксируются одной
          транзакцией.
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
    <p v-if="query.isPending.value" role="status">
      Загрузка оставшегося плана…
    </p>
    <div
      v-if="scope.error.value || query.error.value"
      role="alert"
      class="shrink-0 rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ scope.error.value || query.error.value?.message
      }}<Button
        variant="outline"
        :disabled="pending || query.isFetching.value || !scope.ready.value"
        @click="query.refetch()"
        >Повторить</Button
      >
    </div>
    <div
      v-if="values && scope.ready.value"
      class="flex w-full max-w-5xl shrink-0 flex-col gap-5"
    >
      <p class="text-sm text-muted-foreground">
        Основание формы: версия {{ values.expectedVersion }}. Остатки плана
        вычислены сервером; для SERIAL выбирается каждый экземпляр по 1 PCS.
      </p>
      <p
        v-if="!receivable && !attempt.uncertain"
        role="alert"
        class="text-sm text-destructive"
      >
        Текущий статус документа не допускает приёмку. Введённый факт сохранён
        для сверки.
      </p>
      <div
        v-if="conflict && !attempt.uncertain"
        role="alert"
        class="rounded-md bg-muted p-3 text-sm"
      >
        Конфликт версии: форма {{ values.expectedVersion }}, сервер
        {{ serverVersion }}. Ввод не заменён.
        <div class="mt-2 flex flex-wrap gap-2">
          <Button
            variant="outline"
            :disabled="pending || query.isFetching.value"
            @click="query.refetch()"
            >Загрузить актуальный план</Button
          ><Button
            variant="outline"
            :disabled="
              pending ||
              !!query.error.value ||
              query.data.value?.version !== serverVersion
            "
            @click="replacePlan"
            >Принять актуальный план</Button
          >
        </div>
      </div>
      <p
        v-if="attempt.uncertain"
        role="alert"
        class="rounded-md bg-muted p-3 text-sm"
      >
        Результат запроса неизвестен. Повтор исходной команды с прежним ключом
        не создаст второй факт. Поля сохранены и заблокированы.
      </p>
      <form
        class="flex shrink-0 flex-col gap-5 rounded-lg border bg-card p-4 sm:p-6"
        @submit.prevent="submit"
      >
        <p
          v-if="uoms.error.value"
          role="alert"
          class="text-sm text-destructive"
        >
          {{ uoms.error.value.message
          }}<Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="uoms.refetch()"
            >Повторить загрузку единиц</Button
          >
        </p>
        <ReceiptIntakeLinesForm
          :rows="values.rows"
          :disabled="disabled"
          :errors="errors"
          :uoms="uoms.data.value ?? []"
          @change="changeRow"
          @remove="removeRow"
          @split="splitRow"
          @pick="openPicker"
        />
        <details class="rounded-md border p-3">
          <summary class="cursor-pointer text-sm">
            Общая сумма без распределения
          </summary>
          <label class="mt-3 flex items-center gap-2 text-sm"
            ><input
              v-model="values.unallocatedCost.known"
              type="checkbox"
              :disabled="disabled"
            />Сумма известна, распределение по строкам пока неизвестно</label
          >
          <div
            v-if="values.unallocatedCost.known"
            class="mt-3 grid gap-3 sm:grid-cols-2"
          >
            <label class="text-sm"
              >Нераспределённая сумма<Input
                v-model="values.unallocatedCost.amount"
                type="text"
                inputmode="decimal"
                :disabled="disabled" /></label
            ><label class="text-sm"
              >Валюта общей суммы<Input
                v-model="values.unallocatedCost.currency"
                maxlength="3"
                :disabled="disabled" /></label
            ><label class="text-sm sm:col-span-2"
              >Основание общей суммы<Input
                v-model="values.unallocatedCost.reference"
                maxlength="200"
                :disabled="disabled"
            /></label>
          </div>
          <p
            v-if="errors.costs"
            role="alert"
            class="mt-2 text-sm text-destructive"
          >
            {{ errors.costs }}
          </p>
        </details>
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
      :count="values.rows.length"
      :pending="pending"
      :uncertain="attempt.uncertain"
      :error="error"
      @close="!pending && (confirmOpen = false)"
      @confirm="perform"
    />
  </section>
</template>
