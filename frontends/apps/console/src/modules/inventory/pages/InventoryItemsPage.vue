<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { inventoryItemEditLocation } from "../model/inventory-item-navigation";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryItemsPageState } from "../model/use-inventory-items-page-state";
import { useInventoryItemsQuery } from "../model/use-inventory-items-query";
import InventoryItemsHeader from "../ui/page/InventoryItemsHeader.vue";
import InventoryItemsToolbar from "../ui/page/InventoryItemsToolbar.vue";
import InventoryItemsFooter from "../ui/page/InventoryItemsFooter.vue";
import InventoryItemsBody from "../ui/results/InventoryItemsBody.vue";
import CreateInventoryItemDialog from "../ui/forms/CreateInventoryItemDialog.vue";
import { useCreateInventoryItem } from "../model/use-create-inventory-item";
import { InventoryItemCreateError } from "../model/inventory-item-create.errors";

const scope = useInventoryScope();
const route = useRoute(),
  router = useRouter();
function edit(id: string): void {
  void router.push(inventoryItemEditLocation(id, route.fullPath));
}
const state = useInventoryItemsPageState(scope.key);
const query = useInventoryItemsQuery(state.listParams, scope);
const creation = useCreateInventoryItem(scope);
const createOpen = ref(false),
  createSku = ref(""),
  createError = ref(""),
  skuError = ref(""),
  createPending = ref(false),
  createUncertain = ref(false);
const creationIdentity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value]),
);
let createRequest: AbortController | null = null;
function clearCreation(): void {
  createRequest?.abort();
  createRequest = null;
  createOpen.value = false;
  createSku.value = "";
  createError.value = "";
  skuError.value = "";
  createPending.value = false;
  createUncertain.value = false;
  creation.reset();
}
watch(creationIdentity, clearCreation, { flush: "sync" });
function showCreate(): void {
  if (!scope.ready.value || createPending.value) return;
  clearCreation();
  createOpen.value = true;
}
function closeCreate(): void {
  if (!createPending.value) clearCreation();
}
function changeCreateSku(value: string): void {
  if (createPending.value || createUncertain.value) return;
  createSku.value = value;
  skuError.value = "";
  createError.value = "";
}
async function create(): Promise<void> {
  if (
    !createOpen.value ||
    !scope.ready.value ||
    createPending.value ||
    createUncertain.value
  )
    return;
  if (!createSku.value.trim()) {
    skuError.value = "Укажите код SKU.";
    return;
  }
  const captured = creationIdentity.value,
    returnTo = route.fullPath;
  const controller = new AbortController();
  createRequest = controller;
  createPending.value = true;
  createError.value = "";
  skuError.value = "";
  try {
    const result = await creation.mutateAsync({
      values: { sku: createSku.value },
      scope: [...scope.key.value],
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== creationIdentity.value)
      return;
    createRequest = null;
    createPending.value = false;
    createOpen.value = false;
    void router.push(inventoryItemEditLocation(result.id, returnTo));
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== creationIdentity.value)
      return;
    createUncertain.value =
      !(cause instanceof InventoryItemCreateError) || cause.uncertain;
    createError.value = createUncertain.value
      ? "Результат создания не подтверждён. Проверьте список перед новой попыткой."
      : cause instanceof Error
        ? cause.message
        : "Не удалось создать складскую позицию.";
    if (cause instanceof InventoryItemCreateError && cause.status === 422) {
      skuError.value = cause.message;
      createError.value = "";
    }
  } finally {
    if (createRequest === controller) {
      createRequest = null;
      createPending.value = false;
    }
  }
}
function checkCreated(): void {
  const code = createSku.value;
  closeCreate();
  state.setSearch(code);
  state.submitSearch();
  refresh();
}
onBeforeRouteLeave(() => !createPending.value);
onBeforeRouteUpdate(() => !createPending.value);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (createPending.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => {
  createRequest?.abort();
  window.removeEventListener("beforeunload", beforeUnload);
});
const error = computed(
  () => scope.error.value || query.error.value?.message || "",
);
const refreshing = computed(() => query.isFetching.value && !!query.data.value);
const loading = computed(() => query.isPending.value && !error.value);
const outOfRange = computed(
  () => state.params.value.page > 1 && query.data.value?.items.length === 0,
);

function refresh(): void {
  if (scope.ready.value) void query.refetch();
}
</script>

<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    aria-label="Складская номенклатура"
  >
    <InventoryItemsHeader
      :refreshing="query.isFetching.value"
      :disabled="query.isFetching.value || !scope.ready.value"
      :create-disabled="!scope.ready.value || createPending"
      @refresh="refresh"
      @create="showCreate"
    />
    <InventoryItemsToolbar
      :search="state.searchText.value"
      :total="query.data.value?.total"
      @search="state.setSearch"
      @submit="state.submitSearch"
      @clear="state.clearSearch"
    />
    <InventoryItemsBody
      :items="query.data.value?.items ?? []"
      :loading="loading"
      :refreshing="refreshing"
      :error="error"
      :can-retry="scope.ready.value"
      :retry-pending="query.isFetching.value"
      :filtered="!!state.params.value.search"
      :out-of-range="outOfRange"
      @retry="refresh"
      @edit="edit"
      @clear="state.clearSearch"
      @first-page="state.firstPage"
    />
    <InventoryItemsFooter
      v-if="query.data.value && !outOfRange"
      :page="state.params.value.page"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :disabled="query.isFetching.value"
      @change="state.setPagination"
    />
    <CreateInventoryItemDialog
      :open="createOpen"
      :sku="createSku"
      :pending="createPending"
      :disabled="!scope.ready.value"
      :error="createError"
      :sku-error="skuError"
      :uncertain="createUncertain"
      @sku="changeCreateSku"
      @close="closeCreate"
      @submit="create"
      @check="checkCreated"
    />
  </section>
</template>
