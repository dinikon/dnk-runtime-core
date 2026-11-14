<script setup lang="ts">
import { computed, ref, watch, nextTick, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryItemQuery } from "../model/use-inventory-item-query";
import { useStockLotsQuery } from "../model/use-stock-lots-query";
import { useStockLotsPageState } from "../model/use-stock-lots-page-state";
import { useCreateStockLot } from "../model/use-create-stock-lot";
import { InventoryItemsRequestError } from "../model/inventory-item.errors";
import { StockLotRequestError } from "../model/stock-lot.errors";
import {
  allowsStockLots,
  validateStockLot,
} from "../model/stock-lot.validation";
import {
  stockLotLocation,
  stockLotsReturnPath,
} from "../model/stock-lot-navigation";
import type { StockLotValues, StockLotErrors } from "../model/stock-lot.types";
import StockLotsHeader from "../ui/page/StockLotsHeader.vue";
import StockLotsToolbar from "../ui/page/StockLotsToolbar.vue";
import StockLotsFooter from "../ui/page/StockLotsFooter.vue";
import StockLotsBody from "../ui/results/StockLotsBody.vue";
import CreateStockLotDialog from "../ui/forms/CreateStockLotDialog.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const itemId = computed(() =>
  String(route.params.inventoryItemId ?? "").toLowerCase(),
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, itemId.value]),
);
const state = useStockLotsPageState(scope.key, itemId),
  query = useStockLotsQuery(itemId, state.listParams, scope);
const parent = useInventoryItemQuery(itemId, scope),
  creation = useCreateStockLot(itemId, scope);
const empty = (): StockLotValues => ({
  number: "",
  manufacturedOn: "",
  expiresOn: "",
});
const createOpen = ref(false),
  values = ref<StockLotValues>(empty()),
  errors = ref<StockLotErrors>({});
const pending = ref(false),
  uncertain = ref(false),
  checking = ref(false),
  error = ref("");
let request: AbortController | null = null;
const busy = computed(() => pending.value || checking.value);
const creationDenied = ref(false);
const denied = computed(
  () =>
    !scope.ready.value ||
    (query.error.value instanceof StockLotRequestError &&
      [403, 404].includes(query.error.value.status ?? 0)) ||
    creationDenied.value ||
    (parent.error.value instanceof InventoryItemsRequestError &&
      [403, 404].includes(parent.error.value.status ?? 0)),
);
const currentParent = computed(() =>
  !denied.value ? parent.data.value : undefined,
);
const canCreate = computed(
  () =>
    !!currentParent.value && allowsStockLots(currentParent.value.trackingMode),
);
const rows = computed(() =>
  denied.value ? [] : (query.data.value?.items ?? []),
);
const dirty = computed(
  () => createOpen.value && Object.values(values.value).some(Boolean),
);
function reset(): void {
  request?.abort();
  request = null;
  createOpen.value = false;
  values.value = empty();
  errors.value = {};
  pending.value = false;
  checking.value = false;
  uncertain.value = false;
  error.value = "";
  creation.reset();
}
watch(
  identity,
  () => {
    creationDenied.value = false;
    reset();
  },
  { flush: "sync" },
);
function showCreate(): void {
  if (busy.value || !canCreate.value) return;
  reset();
  state.cancelSearch();
  createOpen.value = true;
  void parent.refetch();
}
function change(next: StockLotValues): void {
  if (busy.value || uncertain.value) return;
  values.value = next;
  errors.value = {};
  error.value = "";
}
function close(): void {
  if (
    !busy.value &&
    (!dirty.value ||
      window.confirm("Закрыть форму и потерять введённые данные?"))
  )
    reset();
}
function openLot(id: string): void {
  if (!busy.value)
    void router.push(stockLotLocation(itemId.value, id, route.fullPath));
}
async function submit(): Promise<void> {
  if (busy.value || uncertain.value || !canCreate.value || !currentParent.value)
    return;
  errors.value = validateStockLot(
    values.value,
    currentParent.value.expirationMode,
  );
  if (Object.keys(errors.value).length) return;
  const captured = identity.value,
    owner = itemId.value,
    snapshot = { ...values.value },
    origin = route.fullPath;
  request = new AbortController();
  pending.value = true;
  error.value = "";
  try {
    const result = await creation.mutateAsync({
      itemId: owner,
      scope: [...scope.key.value],
      values: snapshot,
      signal: request.signal,
    });
    if (captured !== identity.value) return;
    reset();
    await router.push(stockLotLocation(owner, result.id, origin));
  } catch (cause: unknown) {
    if (captured !== identity.value) return;
    error.value =
      cause instanceof Error
        ? cause.message
        : "Не удалось создать партию. Ваш ввод сохранён.";
    if (cause instanceof StockLotRequestError) {
      errors.value = cause.fields;
      uncertain.value = cause.uncertain;
      creationDenied.value = [403, 404].includes(cause.status ?? 0);
    } else uncertain.value = true;
    await parent.refetch();
  } finally {
    if (captured === identity.value) pending.value = false;
  }
}
async function checkResult(): Promise<void> {
  if (busy.value || !uncertain.value) return;
  const captured = identity.value;
  checking.value = true;
  try {
    const result = await parent.refetch();
    if (captured !== identity.value || !result.isSuccess) return;
    createOpen.value = false;
    state.searchAll(values.value.number);
    await nextTick();
    error.value =
      "Результат создания неизвестен. Проверьте точный номер в списке перед новой попыткой.";
    await query.refetch();
  } finally {
    if (captured === identity.value) checking.value = false;
  }
}
function back(): void {
  if (!busy.value)
    void router.push(stockLotsReturnPath(itemId.value, route.query.returnTo));
}
async function refresh(): Promise<void> {
  if (busy.value) return;
  const captured = identity.value;
  const [owner, listing] = await Promise.all([
    parent.refetch(),
    query.refetch(),
  ]);
  if (captured === identity.value && owner.isSuccess && listing.isSuccess)
    creationDenied.value = false;
}
function allowLeave(): boolean {
  return (
    !busy.value &&
    (!dirty.value || window.confirm("Уйти и потерять введённые данные партии?"))
  );
}
onBeforeRouteLeave(allowLeave);
onBeforeRouteUpdate(
  (to, from) =>
    !scope.ready.value ||
    (!pending.value &&
      (to.params.inventoryItemId === from.params.inventoryItemId ||
        allowLeave())),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (busy.value || dirty.value) {
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
    aria-label="Партии SKU"
  >
    <StockLotsHeader
      :sku="currentParent?.sku"
      :busy="busy"
      :create-disabled="!canCreate || createOpen"
      @back="back"
      @create="showCreate"
      @refresh="refresh"
    />
    <Alert v-if="currentParent && !allowsStockLots(currentParent.trackingMode)"
      ><AlertDescription
        >Создание партий доступно только для SKU с партийным учётом LOT или
        LOT_AND_SERIAL.</AlertDescription
      ></Alert
    >
    <Alert v-if="!createOpen && error"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <StockLotsToolbar
      :search="state.searchText.value"
      :disabled="busy || denied || createOpen"
      @change="state.setSearch"
      @submit="state.submitSearch"
      @clear="state.clearSearch"
    />
    <StockLotsBody
      :items="rows"
      :loading="query.isPending.value && scope.ready.value"
      :refreshing="query.isFetching.value && !query.isPending.value"
      :error="
        scope.error.value ||
        parent.error.value?.message ||
        query.error.value?.message ||
        ''
      "
      :disabled="busy || createOpen || denied"
      :can-retry="scope.ready.value"
      :filtered="!!state.params.value.search"
      :out-of-range="state.params.value.page > 1"
      @retry="refresh"
      @clear="state.clearFilters"
      @first-page="state.firstPage"
      @open="openLot"
    />
    <StockLotsFooter
      :page="state.params.value.page"
      :limit="state.params.value.limit"
      :total="denied ? 0 : (query.data.value?.total ?? 0)"
      :disabled="busy || denied || createOpen || query.isFetching.value"
      @change="state.setPagination"
    />
    <CreateStockLotDialog
      :open="createOpen"
      :sku="currentParent?.sku ?? ''"
      :values="values"
      :errors="errors"
      :pending="busy"
      :disabled="!canCreate"
      :uncertain="uncertain"
      :error="error"
      :expiration-mode="currentParent?.expirationMode ?? 'NONE'"
      @close="close"
      @change="change"
      @submit="submit"
      @check="checkResult"
      @refresh="refresh"
    />
  </section>
</template>
