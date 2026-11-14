<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import StockLotBody from "../ui/results/StockLotBody.vue";
import StockLotDatesEditorForm from "../ui/forms/StockLotDatesEditorForm.vue";
import { InventoryItemsRequestError } from "../model/inventory-item.errors";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryItemQuery } from "../model/use-inventory-item-query";
import { useStockLotQuery } from "../model/use-stock-lots-query";
import { stockLotsReturnPath } from "../model/stock-lot-navigation";
import { StockLotRequestError } from "../model/stock-lot.errors";
import { stockLotDatesValues } from "../model/stock-lot-dates-draft";
import { useStockLotDatesDraft } from "../model/use-stock-lot-dates-draft";
import { useUpdateStockLot } from "../model/use-update-stock-lot";
import {
  allowsStockLots,
  validateStockLotDates,
} from "../model/stock-lot.validation";
import type {
  StockLotDatesValues,
  StockLotDatesErrors,
} from "../model/stock-lot.types";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const itemId = computed(() =>
  String(route.params.inventoryItemId ?? "").toLowerCase(),
);
const lotId = computed(() => String(route.params.lotId ?? "").toLowerCase());
const identity = computed(() =>
  JSON.stringify([
    ...scope.key.value,
    scope.ready.value,
    itemId.value,
    lotId.value,
  ]),
);
const query = useStockLotQuery(itemId, lotId, scope),
  parent = useInventoryItemQuery(itemId, scope);
const mutation = useUpdateStockLot(itemId, lotId, scope);
const pending = ref(false),
  checking = ref(false),
  uncertain = ref(false),
  blocked = ref(false);
const error = ref(""),
  notice = ref(""),
  fields = ref<StockLotDatesErrors>({});
const busy = computed(() => pending.value || checking.value);
const inaccessible = computed(
  () =>
    blocked.value ||
    (query.error.value instanceof StockLotRequestError &&
      [403, 404].includes(query.error.value.status ?? 0)) ||
    (parent.error.value instanceof InventoryItemsRequestError &&
      [403, 404].includes(parent.error.value.status ?? 0)),
);
const lot = computed(() =>
  scope.ready.value && !inaccessible.value ? query.data.value : undefined,
);
const owner = computed(() =>
  scope.ready.value && !inaccessible.value ? parent.data.value : undefined,
);
const canEdit = computed(
  () =>
    !!lot.value && !!owner.value && allowsStockLots(owner.value.trackingMode),
);
const draft = useStockLotDatesDraft(
  () => (lot.value ? stockLotDatesValues(lot.value) : undefined),
  identity,
  busy,
);
let request: AbortController | null = null;
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    pending.value = false;
    checking.value = false;
    uncertain.value = false;
    blocked.value = false;
    error.value = "";
    notice.value = "";
    fields.value = {};
    mutation.reset();
  },
  { flush: "sync" },
);
function change(value: StockLotDatesValues): void {
  if (!canEdit.value || checking.value) return;
  draft.change(value);
  fields.value = {};
  error.value = "";
  notice.value = "";
}
function reset(): void {
  if (busy.value || uncertain.value) return;
  draft.reset();
  fields.value = {};
  error.value = "";
  notice.value = "";
}
async function save(): Promise<void> {
  if (
    !canEdit.value ||
    busy.value ||
    uncertain.value ||
    !draft.values.value ||
    !draft.dirty.value ||
    !owner.value
  )
    return;
  fields.value = validateStockLotDates(
    draft.values.value,
    owner.value.expirationMode,
  );
  if (Object.keys(fields.value).length) return;
  const captured = identity.value,
    sent = { ...draft.values.value },
    changes = { ...draft.changes.value };
  request = new AbortController();
  pending.value = true;
  error.value = "";
  notice.value = "";
  try {
    const result = await mutation.mutateAsync({
      scope: [...scope.key.value],
      itemId: itemId.value,
      lotId: lotId.value,
      changes,
      signal: request.signal,
    });
    if (captured !== identity.value) return;
    draft.acknowledge(sent, stockLotDatesValues(result));
    notice.value = "Даты партии сохранены.";
  } catch (cause: unknown) {
    if (captured !== identity.value) return;
    error.value =
      cause instanceof Error
        ? cause.message
        : "Не удалось подтвердить сохранение дат.";
    uncertain.value =
      !(cause instanceof StockLotRequestError) || cause.uncertain;
    if (cause instanceof StockLotRequestError) {
      const errors: StockLotDatesErrors = {};
      for (const key of ["manufacturedOn", "expiresOn"] as const)
        if (draft.values.value?.[key] === sent[key])
          errors[key] = cause.fields[key];
      fields.value = errors;
      if ([403, 404].includes(cause.status ?? 0)) {
        blocked.value = true;
        draft.clear();
      }
    }
    await parent.refetch();
  } finally {
    if (captured === identity.value) pending.value = false;
  }
}
async function refresh(): Promise<void> {
  if (busy.value) return;
  const captured = identity.value,
    reconcile = uncertain.value;
  checking.value = true;
  try {
    const [saved, currentOwner] = await Promise.all([
      query.refetch(),
      parent.refetch(),
    ]);
    if (captured !== identity.value) return;
    if (saved.isSuccess && saved.data && currentOwner.isSuccess) {
      blocked.value = false;
      if (reconcile) {
        draft.rebase(stockLotDatesValues(saved.data));
        uncertain.value = false;
        error.value = "";
        fields.value = {};
        notice.value =
          "Сохранённые данные проверены. Оставшиеся изменения можно сохранить.";
      }
    }
  } finally {
    if (captured === identity.value) checking.value = false;
  }
}
function back(): void {
  if (!busy.value)
    void router.push(
      stockLotsReturnPath(itemId.value, route.query.returnTo, true),
    );
}
function allowLeave(): boolean {
  return (
    !scope.ready.value ||
    (!busy.value &&
      (!draft.dirty.value ||
        window.confirm("Уйти и потерять несохранённые даты партии?")))
  );
}
onBeforeRouteLeave(allowLeave);
onBeforeRouteUpdate(
  (to, from) =>
    (to.params.inventoryItemId === from.params.inventoryItemId &&
      to.params.lotId === from.params.lotId &&
      !busy.value) ||
    allowLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (busy.value || draft.dirty.value) {
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
    class="flex min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Карточка партии"
  >
    <header class="flex flex-wrap items-start gap-3">
      <Button variant="outline" :disabled="busy" @click="back"
        >Назад к партиям</Button
      >
      <div class="min-w-0 flex-1">
        <h1 class="text-xl font-semibold">Карточка партии</h1>
        <p v-if="owner" class="break-all font-mono text-sm">{{ owner.sku }}</p>
      </div>
      <Button
        variant="outline"
        :disabled="
          busy ||
          query.isFetching.value ||
          parent.isFetching.value ||
          !scope.ready.value
        "
        @click="refresh"
        >Обновить</Button
      >
    </header>
    <Alert v-if="owner && !allowsStockLots(owner.trackingMode)"
      ><AlertDescription
        >Изменение дат доступно только при LOT или LOT_AND_SERIAL. Сохранённая
        партия доступна для просмотра.</AlertDescription
      ></Alert
    >
    <p v-if="notice" role="status" class="text-sm">{{ notice }}</p>
    <StockLotBody
      :lot="lot"
      :loading="query.isPending.value && scope.ready.value"
      :error="
        scope.error.value ||
        (inaccessible && error ? error : '') ||
        query.error.value?.message ||
        parent.error.value?.message ||
        ''
      "
      :refreshing="query.isFetching.value || parent.isFetching.value"
      @retry="refresh"
    >
      <StockLotDatesEditorForm
        v-if="lot && draft.values.value"
        :number="lot.number"
        :values="draft.values.value"
        :errors="fields"
        :pending="pending"
        :checking="checking"
        :disabled="!canEdit"
        :uncertain="uncertain"
        :dirty="draft.dirty.value"
        :error="error"
        :expiration-mode="owner?.expirationMode ?? 'NONE'"
        @change="change"
        @submit="save"
        @reset="reset"
        @verify="refresh"
      />
    </StockLotBody>
  </section>
</template>
