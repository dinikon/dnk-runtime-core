<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount, onMounted } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useInventoryItemDeletion } from "../model/use-inventory-item-deletion";
import { InventoryItemsRequestError } from "../model/inventory-item.errors";
import type { InventoryItemDeleteTarget } from "../model/inventory-item-editor.types";
import DeleteInventoryItemDialog from "../ui/forms/DeleteInventoryItemDialog.vue";
import { itemPackagingsLocation } from "../model/item-packaging-navigation";
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
function packagings(id: string): void {
  if (busy.value || deletion.target.value || createOpen.value) return;
  void router.push(itemPackagingsLocation(id, route.fullPath));
}
function edit(id: string): void {
  if (busy.value || deletion.target.value || createOpen.value) return;
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
const deletion = useInventoryItemDeletion(
  creationIdentity,
  scope,
  afterRemoval,
);
const notice = ref(""),
  reloading = ref(false),
  reconcilePath = ref("");
const busy = computed(
  () => createPending.value || deletion.pending.value || reloading.value,
);
const forbidden = computed(
  () =>
    !scope.ready.value ||
    deletion.blocked.value ||
    (query.error.value instanceof InventoryItemsRequestError &&
      [403, 404].includes(query.error.value.status ?? 0)),
);
function showDelete(value: InventoryItemDeleteTarget): void {
  if (busy.value || createOpen.value || forbidden.value) return;
  state.cancelSearch();
  deletion.open(value);
}
function afterRemoval(alreadyGone: boolean): void {
  notice.value = alreadyGone
    ? "Складская позиция уже удалена."
    : "Складская позиция удалена.";
  reconcilePath.value = route.fullPath;
  void readList();
}
async function readList(): Promise<void> {
  const captured = creationIdentity.value,
    path = route.fullPath,
    reconcile = reconcilePath.value === path;
  if (reconcile) reloading.value = true;
  try {
    const result = await query.refetch({ throwOnError: false });
    if (
      captured === creationIdentity.value &&
      path === route.fullPath &&
      reconcile &&
      result.isSuccess &&
      result.data
    ) {
      reconcilePath.value = "";
      reloading.value = false;
      state.reconcilePage(result.data.total);
    }
  } finally {
    if (captured === creationIdentity.value && reconcile)
      reloading.value = false;
  }
}
// Одноразовый контекст перехода после удаления из редактора, без служебных query-параметров.
onMounted(() => {
  const marker: unknown = window.history.state?.inventoryItemDeletionScope;
  if (marker !== undefined) {
    const historyState = { ...window.history.state };
    delete historyState.inventoryItemDeletionScope;
    window.history.replaceState(historyState, "");
    if (marker === JSON.stringify(scope.key.value)) {
      reconcilePath.value = route.fullPath;
      void readList();
    }
  }
});
watch(
  creationIdentity,
  () => {
    notice.value = "";
    reloading.value = false;
    reconcilePath.value = "";
  },
  { flush: "sync" },
);
watch(
  () => route.fullPath,
  () => {
    reconcilePath.value = "";
  },
  { flush: "sync" },
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
  if (!scope.ready.value || busy.value || !!deletion.target.value || forbidden.value) return;
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
    forbidden.value ||
    !scope.ready.value ||
    busy.value ||
    !!deletion.target.value ||
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
onBeforeRouteLeave(() => !busy.value);
onBeforeRouteUpdate(() => !busy.value);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (busy.value) {
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
  if (scope.ready.value && !busy.value) void readList();
}
</script>

<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    aria-label="Складская номенклатура"
  >
    <InventoryItemsHeader
      :refreshing="query.isFetching.value"
      :disabled="query.isFetching.value || !scope.ready.value || busy"
      :create-disabled="
        !scope.ready.value || busy || !!deletion.target.value || forbidden
      "
      @refresh="refresh"
      @create="showCreate"
    />
    <p v-if="notice" role="status" class="text-sm text-muted-foreground">
      {{ notice }}
    </p>
    <Alert v-if="deletion.blocked.value" variant="destructive"
      ><AlertDescription>{{ deletion.error.value }}</AlertDescription></Alert
    >
    <InventoryItemsToolbar
      :disabled="busy || !!deletion.target.value"
      :search="state.searchText.value"
      :total="forbidden ? undefined : query.data.value?.total"
      @search="state.setSearch"
      @submit="state.submitSearch"
      @clear="state.clearSearch"
    />
    <InventoryItemsBody
      :items="forbidden ? [] : (query.data.value?.items ?? [])"
      :disabled="busy || !!deletion.target.value || createOpen"
      :loading="loading"
      :refreshing="refreshing"
      :error="error"
      :can-retry="scope.ready.value"
      :retry-pending="query.isFetching.value || busy"
      :filtered="!!state.params.value.search"
      :out-of-range="outOfRange"
      @retry="refresh"
      @edit="edit"
      @packagings="packagings"
      @delete="showDelete"
      @clear="state.clearSearch"
      @first-page="state.firstPage"
    />
    <InventoryItemsFooter
      v-if="query.data.value && !outOfRange && !forbidden"
      :page="state.params.value.page"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :disabled="query.isFetching.value || busy || !!deletion.target.value"
      @change="state.setPagination"
    />
    <DeleteInventoryItemDialog
      v-if="deletion.target.value"
      :item="deletion.target.value"
      :pending="deletion.pending.value"
      :uncertain="deletion.uncertain.value"
      :error="deletion.error.value"
      @close="deletion.close"
      @confirm="deletion.confirm"
      @check="deletion.check"
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
