<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useWarehousesPageState } from "../model/use-warehouses-page-state";
import { useWarehousesQuery } from "../model/use-warehouses-query";
import { useCreateWarehouse } from "../model/use-create-warehouse";
import { warehouseEditLocation } from "../model/warehouse-navigation";
import { validateWarehouse } from "../model/warehouse-form.validation";
import { WarehouseRequestError } from "../model/warehouse.errors";
import type {
  WarehouseCreateValues,
  WarehouseFieldErrors,
} from "../model/warehouse.types";
import WarehousesHeader from "../ui/page/WarehousesHeader.vue";
import WarehousesToolbar from "../ui/page/WarehousesToolbar.vue";
import WarehousesFooter from "../ui/page/WarehousesFooter.vue";
import WarehousesBody from "../ui/results/WarehousesBody.vue";
import CreateWarehouseDialog from "../ui/forms/CreateWarehouseDialog.vue";

const scope = useInventoryScope(),
  route = useRoute(),
  router = useRouter();
const state = useWarehousesPageState(scope.key),
  query = useWarehousesQuery(state.listParams, scope),
  creation = useCreateWarehouse(scope);
const createOpen = ref(false),
  values = ref<WarehouseCreateValues>({ code: "", name: "" }),
  errors = ref<WarehouseFieldErrors>({});
const pending = ref(false),
  uncertain = ref(false),
  createError = ref("");
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value]),
);
let request: AbortController | null = null;
function clearCreation(): void {
  request?.abort();
  request = null;
  createOpen.value = false;
  pending.value = false;
  uncertain.value = false;
  values.value = { code: "", name: "" };
  errors.value = {};
  createError.value = "";
  creation.reset();
}
watch(identity, clearCreation, { flush: "sync" });
function showCreate(): void {
  if (!scope.ready.value || pending.value) return;
  clearCreation();
  createOpen.value = true;
}
function closeCreate(): void {
  if (!pending.value) clearCreation();
}
function change(valuesAfter: WarehouseCreateValues): void {
  if (pending.value || uncertain.value) return;
  values.value = valuesAfter;
  errors.value = {};
  createError.value = "";
}
function edit(id: string): void {
  void router.push(warehouseEditLocation(id, route.fullPath));
}
function refresh(): void {
  if (scope.ready.value) void query.refetch();
}
async function create(): Promise<void> {
  if (
    !createOpen.value ||
    !scope.ready.value ||
    pending.value ||
    uncertain.value
  )
    return;
  errors.value = validateWarehouse(values.value);
  if (Object.keys(errors.value).length) return;
  const captured = identity.value,
    returnTo = route.fullPath,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  createError.value = "";
  try {
    const result = await creation.mutateAsync({
      values: { ...values.value },
      scope: [...scope.key.value],
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== identity.value) return;
    request = null;
    pending.value = false;
    createOpen.value = false;
    void router.push(warehouseEditLocation(result.id, returnTo));
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    uncertain.value =
      !(cause instanceof WarehouseRequestError) || cause.uncertain;
    errors.value = cause instanceof WarehouseRequestError ? cause.fields : {};
    createError.value = uncertain.value
      ? "Результат создания не подтверждён. Проверьте список перед новой попыткой."
      : cause instanceof Error
        ? cause.message
        : "Не удалось создать склад.";
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
  () => scope.error.value || query.error.value?.message || "",
);
const loading = computed(() => query.isPending.value && !error.value);
const refreshing = computed(() => query.isFetching.value && !!query.data.value);
const outOfRange = computed(
  () => state.params.value.page > 1 && query.data.value?.items.length === 0,
);
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    aria-label="Склады"
  >
    <WarehousesHeader
      :refreshing="query.isFetching.value"
      :disabled="query.isFetching.value || !scope.ready.value"
      :create-disabled="!scope.ready.value || pending"
      @refresh="refresh"
      @create="showCreate"
    />
    <WarehousesToolbar
      :search="state.searchText.value"
      :activity="state.params.value.activity"
      :total="query.data.value?.total"
      @search="state.setSearch"
      @submit="state.submitSearch"
      @clear="state.clearSearch"
      @activity="state.setActivity"
    />
    <WarehousesBody
      :items="query.data.value?.items ?? []"
      :loading="loading"
      :refreshing="refreshing"
      :error="error"
      :can-retry="scope.ready.value"
      :retry-pending="query.isFetching.value"
      :filtered="
        !!state.params.value.search || state.params.value.activity !== 'all'
      "
      :out-of-range="outOfRange"
      @retry="refresh"
      @edit="edit"
      @clear="state.clearFilters"
      @first-page="state.firstPage"
    />
    <WarehousesFooter
      v-if="query.data.value && !outOfRange"
      :page="state.params.value.page"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :disabled="query.isFetching.value"
      @change="state.setPagination"
    />
    <CreateWarehouseDialog
      :open="createOpen"
      :values="values"
      :errors="errors"
      :pending="pending"
      :disabled="!scope.ready.value"
      :uncertain="uncertain"
      :error="createError"
      @change="change"
      @submit="create"
      @close="closeCreate"
      @check="checkCreated"
    />
  </section>
</template>
