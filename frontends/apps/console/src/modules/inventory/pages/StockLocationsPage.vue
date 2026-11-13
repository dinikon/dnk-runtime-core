<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useWarehouseQuery } from "../model/use-warehouse-query";
import { WarehouseRequestError } from "../model/warehouse.errors";
import { useStockLocationsPageState } from "../model/use-stock-locations-page-state";
import { useStockLocationsQuery } from "../model/use-stock-locations-query";
import { useStockLocationQuery } from "../model/use-stock-location-query";
import { useStockLocationParentSearch } from "../model/use-stock-location-parent-search";
import { useCreateStockLocation } from "../model/use-create-stock-location";
import {
  stockLocationRouteId,
  stockLocationEditLocation,
  warehouseLocationsReturnPath,
} from "../model/stock-location-navigation";
import { validateStockLocationCreate } from "../model/stock-location-form.validation";
import { isStockLocationType } from "../model/stock-location.constants";
import {
  StockLocationRequestError,
  stockLocationUnavailable,
} from "../model/stock-location.errors";
import type {
  StockLocationCreateFormValues,
  StockLocationFieldErrors,
} from "../model/stock-location.types";
import StockLocationsHeader from "../ui/page/StockLocationsHeader.vue";
import StockLocationsToolbar from "../ui/page/StockLocationsToolbar.vue";
import StockLocationsFooter from "../ui/page/StockLocationsFooter.vue";
import StockLocationsBody from "../ui/results/StockLocationsBody.vue";
import CreateStockLocationDialog from "../ui/forms/CreateStockLocationDialog.vue";
import StockLocationParentPicker from "../ui/forms/StockLocationParentPicker.vue";

const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const warehouseId = computed(() =>
  stockLocationRouteId(route.params.warehouseId),
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, warehouseId.value]),
);
const warehouse = useWarehouseQuery(warehouseId, scope);
const state = useStockLocationsPageState(scope.key, warehouseId);
const query = useStockLocationsQuery(warehouseId, state.listParams, scope);
const creation = useCreateStockLocation(warehouseId, scope);
const warehouseMissing = computed(
  () =>
    warehouse.error.value instanceof WarehouseRequestError &&
    [403, 404].includes(warehouse.error.value.status ?? 0),
);
const currentWarehouse = computed(() =>
  scope.ready.value &&
  !warehouse.error.value &&
  warehouse.data.value?.id === warehouseId.value
    ? warehouse.data.value
    : undefined,
);
const canCreate = computed(() => !!currentWarehouse.value?.isActive);
const createOpen = ref(false),
  pending = ref(false),
  uncertain = ref(false),
  createError = ref("");
function emptyValues(): StockLocationCreateFormValues {
  return { code: "", name: "", locationType: "", parentLocationId: null };
}
const values = ref<StockLocationCreateFormValues>(emptyValues()),
  errors = ref<StockLocationFieldErrors>({});
const filterOpen = ref(false);
const filterParentSearch = useStockLocationParentSearch(
  warehouseId,
  filterOpen,
  scope,
  identity,
);
const filterParentId = computed(() => state.params.value.parentLocationId);
const filterParent = useStockLocationQuery(warehouseId, filterParentId, scope);
const createParentSearch = useStockLocationParentSearch(
  warehouseId,
  createOpen,
  scope,
  identity,
);
const createParentId = computed(() => values.value.parentLocationId);
const createParent = useStockLocationQuery(warehouseId, createParentId, scope);
let request: AbortController | null = null;
function clearCreation(): void {
  request?.abort();
  request = null;
  createOpen.value = false;
  pending.value = false;
  uncertain.value = false;
  values.value = emptyValues();
  errors.value = {};
  createError.value = "";
  creation.reset();
  createParentSearch.reset();
}
watch(
  identity,
  () => {
    filterOpen.value = false;
    clearCreation();
  },
  { flush: "sync" },
);
function showCreate(): void {
  if (!canCreate.value || pending.value) return;
  clearCreation();
  values.value.parentLocationId = state.params.value.parentLocationId;
  createOpen.value = true;
}
function closeCreate(): void {
  if (!pending.value) clearCreation();
}
function change(value: StockLocationCreateFormValues): void {
  if (pending.value || uncertain.value) return;
  values.value = value;
  errors.value = {};
  createError.value = "";
}
function selectCreateParent(id: string | null): void {
  change({ ...values.value, parentLocationId: id });
}
function edit(id: string): void {
  void router.push(
    stockLocationEditLocation(warehouseId.value, id, route.fullPath),
  );
}
function back(): void {
  void router.push(
    warehouseLocationsReturnPath(warehouseId.value, route.query.returnTo),
  );
}
function refresh(): void {
  if (scope.ready.value) {
    void warehouse.refetch();
    void query.refetch();
  }
}
function retryFilterParent(): void {
  if (filterParentId.value && scope.ready.value) void filterParent.refetch();
}
function retryCreateParent(): void {
  if (createParentId.value && scope.ready.value) void createParent.refetch();
}
async function create(): Promise<void> {
  if (!createOpen.value || !canCreate.value || pending.value || uncertain.value)
    return;
  errors.value = validateStockLocationCreate(values.value);
  if (
    values.value.parentLocationId &&
    (!createParent.data.value || createParent.error.value)
  )
    errors.value.parentLocationId =
      "Загрузите выбранного родителя или выберите другую локацию.";
  if (
    Object.keys(errors.value).length ||
    !isStockLocationType(values.value.locationType)
  )
    return;
  const captured = identity.value,
    returnTo = route.fullPath,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  createError.value = "";
  try {
    const result = await creation.mutateAsync({
      warehouseId: warehouseId.value,
      scope: [...scope.key.value],
      values: {
        code: values.value.code,
        name: values.value.name,
        locationType: values.value.locationType,
        parentLocationId: values.value.parentLocationId,
      },
      signal: controller.signal,
    });
    if (captured !== identity.value || controller.signal.aborted) return;
    request = null;
    pending.value = false;
    createOpen.value = false;
    void router.push(
      stockLocationEditLocation(warehouseId.value, result.id, returnTo),
    );
  } catch (cause: unknown) {
    if (captured !== identity.value || controller.signal.aborted) return;
    uncertain.value =
      !(cause instanceof StockLocationRequestError) || cause.uncertain;
    errors.value =
      cause instanceof StockLocationRequestError ? cause.fields : {};
    createError.value = uncertain.value
      ? "Результат создания не подтверждён. Проверьте список перед новой попыткой."
      : cause instanceof Error
        ? cause.message
        : "Не удалось создать локацию.";
    void warehouse.refetch();
  } finally {
    if (request === controller) {
      request = null;
      pending.value = false;
    }
  }
}
function checkCreated(): void {
  const code = values.value.code;
  closeCreate();
  state.searchAll(code);
}
onBeforeRouteLeave(() => !pending.value);
onBeforeRouteUpdate(() => !pending.value);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (pending.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => {
  request?.abort();
  window.removeEventListener("beforeunload", beforeUnload);
});
const error = computed(
  () =>
    scope.error.value ||
    warehouse.error.value?.message ||
    query.error.value?.message ||
    "",
);
const forbidden = computed(
  () => warehouseMissing.value || stockLocationUnavailable(query.error.value),
);
const loading = computed(() => query.isPending.value && !error.value);
const outOfRange = computed(
  () => state.params.value.page > 1 && query.data.value?.items.length === 0,
);
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto"
    aria-label="Локации склада"
  >
    <StockLocationsHeader
      :warehouse="currentWarehouse"
      :refreshing="query.isFetching.value || warehouse.isFetching.value"
      :disabled="
        query.isFetching.value ||
        warehouse.isFetching.value ||
        !scope.ready.value
      "
      :create-disabled="!canCreate || pending"
      :pending="pending"
      @refresh="refresh"
      @create="showCreate"
      @back="back"
    />
    <StockLocationsToolbar
      :search="state.searchText.value"
      :activity="state.params.value.activity"
      :location-type="state.params.value.locationType"
      :total="query.data.value?.total"
      @search="state.setSearch"
      @submit="state.submitSearch"
      @clear="state.clearSearch"
      @activity="state.setActivity"
      @type="state.setType"
    >
      <template #parent
        ><StockLocationParentPicker
          id="stock-locations-parent"
          label="Поиск родителя в фильтре"
          empty-label="Все уровни"
          :search="filterParentSearch.search.value"
          :options="filterParentSearch.options.value"
          :total="filterParentSearch.total.value"
          :loading="filterParentSearch.loading.value"
          :fetching-more="filterParentSearch.fetchingMore.value"
          :has-more="filterParentSearch.hasMore.value"
          :error="filterParentSearch.error.value"
          :selected-id="filterParentId"
          :selected="filterParent.data.value"
          :selected-loading="filterParent.isFetching.value"
          :selected-error="filterParent.error.value?.message || ''"
          :disabled="!currentWarehouse || pending"
          @search="filterParentSearch.search.value = $event"
          @open="filterOpen = $event"
          @select="state.setParent"
          @more="filterParentSearch.more"
          @retry="filterParentSearch.retry"
          @retry-selected="retryFilterParent"
      /></template>
    </StockLocationsToolbar>
    <StockLocationsBody
      :items="forbidden ? [] : (query.data.value?.items ?? [])"
      :default-location-id="currentWarehouse?.defaultStorageLocationId"
      :loading="loading"
      :refreshing="query.isFetching.value && !!query.data.value"
      :error="error"
      :can-retry="scope.ready.value"
      :retry-pending="query.isFetching.value || warehouse.isFetching.value"
      :filtered="
        !!state.params.value.search ||
        state.params.value.activity !== 'all' ||
        !!state.params.value.locationType ||
        !!state.params.value.parentLocationId
      "
      :out-of-range="outOfRange"
      @retry="refresh"
      @edit="edit"
      @children="state.showChildren"
      @clear="state.clearFilters"
      @first-page="state.firstPage"
    />
    <StockLocationsFooter
      v-if="query.data.value && !outOfRange && !forbidden"
      :page="state.params.value.page"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :disabled="query.isFetching.value"
      @change="state.setPagination"
    />
    <CreateStockLocationDialog
      :open="createOpen"
      :values="values"
      :errors="errors"
      :pending="pending"
      :disabled="!scope.ready.value"
      :can-create="canCreate"
      :uncertain="uncertain"
      :error="createError"
      @change="change"
      @submit="create"
      @close="closeCreate"
      @check="checkCreated"
    >
      <template #parent
        ><StockLocationParentPicker
          id="stock-location-create-parent"
          label="Поиск родительской локации"
          empty-label="Без родителя"
          :search="createParentSearch.search.value"
          :options="createParentSearch.options.value"
          :total="createParentSearch.total.value"
          :loading="createParentSearch.loading.value"
          :fetching-more="createParentSearch.fetchingMore.value"
          :has-more="createParentSearch.hasMore.value"
          :error="createParentSearch.error.value"
          :selected-id="createParentId"
          :selected="createParent.data.value"
          :selected-loading="createParent.isFetching.value"
          :selected-error="createParent.error.value?.message || ''"
          :disabled="!canCreate || pending || uncertain"
          :invalid="!!errors.parentLocationId"
          @search="createParentSearch.search.value = $event"
          @select="selectCreateParent"
          @more="createParentSearch.more"
          @retry="createParentSearch.retry"
          @retry-selected="retryCreateParent"
      /></template>
    </CreateStockLocationDialog>
  </section>
</template>
