<script setup lang="ts">
import { useStockLotCandidates } from "../model/use-stock-lot-candidates";
import { useStockLotQuery } from "../model/use-stock-lots-query";
import {
  stockLotLocation,
  stockLotsLocation,
} from "../model/stock-lot-navigation";
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import StockSerialBody from "../ui/results/StockSerialBody.vue";
import StockSerialEditorForm from "../ui/forms/StockSerialEditorForm.vue";
import { InventoryItemsRequestError } from "../model/inventory-item.errors";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryItemQuery } from "../model/use-inventory-item-query";
import { useStockSerialQuery } from "../model/use-stock-serials-query";
import { stockSerialsReturnPath } from "../model/stock-serial-navigation";
import { StockSerialRequestError } from "../model/stock-serial.errors";
import { stockSerialValues } from "../model/stock-serial-draft";
import { useStockSerialDraft } from "../model/use-stock-serial-draft";
import { useUpdateStockSerial } from "../model/use-update-stock-serial";
import {
  allowsStockSerials,
  validateStockSerial,
} from "../model/stock-serial.validation";
import type {
  StockSerialValues,
  StockSerialErrors,
} from "../model/stock-serial.types";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const itemId = computed(() =>
  String(route.params.inventoryItemId ?? "").toLowerCase(),
);
const serialId = computed(() =>
  String(route.params.serialId ?? "").toLowerCase(),
);
const identity = computed(() =>
  JSON.stringify([
    ...scope.key.value,
    scope.ready.value,
    itemId.value,
    serialId.value,
  ]),
);
const query = useStockSerialQuery(itemId, serialId, scope),
  parent = useInventoryItemQuery(itemId, scope);
const mutation = useUpdateStockSerial(itemId, serialId, scope);
const editing = ref(false);
const pending = ref(false),
  checking = ref(false),
  uncertain = ref(false),
  blocked = ref(false);
const error = ref(""),
  notice = ref(""),
  fields = ref<StockSerialErrors>({});
const busy = computed(() => pending.value || checking.value);
const inaccessible = computed(
  () =>
    blocked.value ||
    (query.error.value instanceof StockSerialRequestError &&
      [403, 404].includes(query.error.value.status ?? 0)) ||
    (parent.error.value instanceof InventoryItemsRequestError &&
      [403, 404].includes(parent.error.value.status ?? 0)),
);
const serial = computed(() =>
  scope.ready.value && !inaccessible.value ? query.data.value : undefined,
);
const owner = computed(() =>
  scope.ready.value && !inaccessible.value ? parent.data.value : undefined,
);
const canEdit = computed(
  () =>
    !!serial.value &&
    !!owner.value &&
    allowsStockSerials(owner.value.trackingMode),
);
const draft = useStockSerialDraft(
  () => (serial.value ? stockSerialValues(serial.value) : undefined),
  identity,
  busy,
);
const lotRequired = computed(
  () => editing.value && owner.value?.trackingMode === "LOT_AND_SERIAL",
);
const candidates = useStockLotCandidates(itemId, lotRequired, scope);
const selectedId = computed(() =>
  editing.value ? (draft.values.value?.lotId ?? "") : "",
);
const selectedLot = useStockLotQuery(itemId, selectedId, scope);
function startEdit(): void {
  if (canEdit.value && !busy.value) {
    draft.reset();
    editing.value = true;
    fields.value = {};
    error.value = "";
    notice.value = "";
  }
}
function cancelEdit(): void {
  if (busy.value || uncertain.value) return;
  if (
    draft.dirty.value &&
    !window.confirm("Отменить несохранённые изменения экземпляра?")
  )
    return;
  reset();
  editing.value = false;
}
function openLot(id: string): void {
  if (!busy.value)
    void router.push(stockLotLocation(itemId.value, id, route.fullPath));
}
function openLots(): void {
  if (!busy.value)
    void router.push(
      stockLotsLocation(
        itemId.value,
        `/inventory/items/${encodeURIComponent(itemId.value)}`,
      ),
    );
}
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
    editing.value = false;
    mutation.reset();
  },
  { flush: "sync" },
);
function change(value: StockSerialValues): void {
  if (!canEdit.value || checking.value || uncertain.value) return;
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
  fields.value = validateStockSerial(
    draft.values.value,
    owner.value.trackingMode,
  );
  if (Object.keys(fields.value).length) return;
  if (
    owner.value.trackingMode === "LOT_AND_SERIAL" &&
    (selectedLot.isFetching.value ||
      !selectedLot.data.value ||
      selectedLot.isError.value)
  ) {
    fields.value.lotId =
      "Дождитесь загрузки выбранной партии или выберите доступную партию.";
    return;
  }
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
      serialId: serialId.value,
      changes,
      signal: request.signal,
    });
    if (captured !== identity.value) return;
    draft.acknowledge(sent, stockSerialValues(result));
    notice.value = draft.dirty.value
      ? "Изменения сохранены. Есть новые несохранённые правки."
      : "Изменения экземпляра сохранены.";
    if (!draft.dirty.value) editing.value = false;
  } catch (cause: unknown) {
    if (captured !== identity.value) return;
    error.value =
      cause instanceof Error
        ? cause.message
        : "Не удалось подтвердить сохранение экземпляра.";
    uncertain.value =
      !(cause instanceof StockSerialRequestError) || cause.uncertain;
    if (cause instanceof StockSerialRequestError) {
      const errors: StockSerialErrors = {};
      for (const key of ["number", "lotId"] as const)
        if (draft.values.value?.[key] === sent[key])
          errors[key] = cause.fields[key];
      fields.value = errors;
      if (cause.status === 403) {
        blocked.value = true;
        draft.clear();
      }
      if (cause.status === 404)
        await Promise.all([
          query.refetch(),
          ...(selectedId.value ? [selectedLot.refetch()] : []),
        ]);
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
        draft.rebase(stockSerialValues(saved.data));
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
      stockSerialsReturnPath(itemId.value, route.query.returnTo, true),
    );
}
function allowLeave(): boolean {
  return (
    !scope.ready.value ||
    (!busy.value &&
      (!draft.dirty.value ||
        window.confirm("Уйти и потерять несохранённые изменения экземпляра?")))
  );
}
onBeforeRouteLeave(allowLeave);
onBeforeRouteUpdate(
  (to, from) =>
    (to.params.inventoryItemId === from.params.inventoryItemId &&
      to.params.serialId === from.params.serialId &&
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
    aria-label="Карточка серийного экземпляра"
  >
    <header
      class="flex min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start"
    >
      <Button
        class="self-start"
        variant="outline"
        :disabled="busy"
        @click="back"
        >Назад к экземплярам</Button
      >
      <div class="min-w-0 sm:flex-1">
        <h1 class="break-words text-xl font-semibold">
          Карточка серийного экземпляра
        </h1>
        <p v-if="owner" class="break-all font-mono text-sm">{{ owner.sku }}</p>
      </div>
      <div class="flex flex-wrap gap-2 sm:ml-auto">
        <Button v-if="!editing" :disabled="!canEdit || busy" @click="startEdit"
          >Редактировать</Button
        >
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
      </div>
    </header>
    <Alert v-if="owner && !allowsStockSerials(owner.trackingMode)"
      ><AlertDescription
        >Изменение экземпляра доступно только при SERIAL или LOT_AND_SERIAL.
        Сохранённая карточка доступна для просмотра.</AlertDescription
      ></Alert
    >
    <p v-if="notice" role="status" class="text-sm">{{ notice }}</p>
    <StockSerialBody
      :serial="serial"
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
      @lot="openLot"
    >
      <template v-if="editing && serial && draft.values.value" #default>
        <StockSerialEditorForm
          :values="draft.values.value"
          :errors="fields"
          :pending="pending"
          :checking="checking"
          :disabled="!canEdit"
          :uncertain="uncertain"
          :dirty="draft.dirty.value"
          :error="error"
          :mode="owner?.trackingMode ?? 'NONE'"
          :lot-search="candidates.search.value"
          :lots="candidates.items.value"
          :lots-loading="candidates.pending.value"
          :lots-busy="candidates.refreshing.value"
          :lots-error="candidates.error.value"
          :has-more-lots="candidates.hasMore.value"
          :selected-lot="
            selectedLot.isError.value ? undefined : selectedLot.data.value
          "
          :selected-lot-error="selectedLot.error.value?.message ?? ''"
          @search-lots="candidates.setSearch"
          @more-lots="candidates.more"
          @retry-lots="candidates.retry"
          @retry-selected="selectedLot.refetch()"
          @lots="openLots"
          @refresh="refresh"
          @change="change"
          @submit="save"
          @cancel="cancelEdit"
          @verify="refresh"
        />
      </template>
    </StockSerialBody>
  </section>
</template>
