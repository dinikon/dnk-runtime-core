<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useItemPackagingDeletion } from "../model/use-item-packaging-deletion";
import DeleteItemPackagingDialog from "../ui/forms/DeleteItemPackagingDialog.vue";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useItemPackagingsPageState } from "../model/use-item-packagings-page-state";
import { useItemPackagingsQuery } from "../model/use-item-packagings-query";
import { useCreateItemPackaging } from "../model/use-create-item-packaging";
import { useItemPackagingFormContext } from "../model/use-item-packaging-form-context";
import {
  itemPackagingEditLocation,
  itemPackagingsReturnPath,
} from "../model/item-packaging-navigation";
import { validateItemPackaging } from "../model/item-packaging.validation";
import { ItemPackagingRequestError } from "../model/item-packaging.errors";
import type {
  ItemPackaging,
  ItemPackagingValues,
  ItemPackagingErrors,
} from "../model/item-packaging.types";
import ItemPackagingsHeader from "../ui/page/ItemPackagingsHeader.vue";
import ItemPackagingsToolbar from "../ui/page/ItemPackagingsToolbar.vue";
import ItemPackagingsFooter from "../ui/page/ItemPackagingsFooter.vue";
import ItemPackagingsBody from "../ui/results/ItemPackagingsBody.vue";
import ItemPackagingContext from "../ui/results/ItemPackagingContext.vue";
import CreateItemPackagingDialog from "../ui/forms/CreateItemPackagingDialog.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const itemId = computed(() =>
  String(route.params.inventoryItemId ?? "").toLowerCase(),
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, itemId.value]),
);
const state = useItemPackagingsPageState(scope.key, itemId),
  query = useItemPackagingsQuery(itemId, state.listParams, scope),
  creation = useCreateItemPackaging(itemId, scope);
const empty = (): ItemPackagingValues => ({
  packagingTypeId: "",
  code: "",
  name: "",
  contentQuantity: "",
  contentUom: "",
});
const createOpen = ref(false),
  values = ref<ItemPackagingValues>(empty()),
  errors = ref<ItemPackagingErrors>({});
const pending = ref(false),
  uncertain = ref(false),
  createError = ref(""),
  typeOpen = ref(false);
const notice = ref("");
const reloading = ref(false),
  reconcilePath = ref("");
const deletion = useItemPackagingDeletion(
  itemId,
  identity,
  scope,
  afterRemoval,
);
const busy = computed(
  () => pending.value || deletion.pending.value || reloading.value,
);
function afterRemoval(alreadyGone: boolean): void {
  notice.value = alreadyGone ? "Упаковка уже удалена." : "Упаковка удалена.";
  reconcilePath.value = route.fullPath;
  void readList();
}
async function readList(): Promise<void> {
  const captured = identity.value,
    path = route.fullPath;
  const reconcile = reconcilePath.value === path;
  if (reconcile) reloading.value = true;
  try {
    const result = await query.refetch({ throwOnError: false });
    if (
      captured === identity.value &&
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
    if (captured === identity.value && reconcile) reloading.value = false;
  }
}
function showDelete(value: ItemPackaging): void {
  if (
    busy.value ||
    createOpen.value ||
    forbidden.value ||
    !context.currentParent.value
  )
    return;
  state.cancelSearch();
  deletion.open(value);
}
watch(
  identity,
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
const typeId = computed(() => values.value.packagingTypeId);
const context = useItemPackagingFormContext(
  itemId,
  typeId,
  typeOpen,
  identity,
  scope,
);
const forbidden = computed(
  () =>
    !scope.ready.value ||
    deletion.blocked.value ||
    context.parentMissing.value ||
    (query.error.value instanceof ItemPackagingRequestError &&
      [403, 404].includes(query.error.value.status ?? 0)),
);
let request: AbortController | null = null;
function clearCreation(): void {
  request?.abort();
  request = null;
  createOpen.value = false;
  pending.value = false;
  uncertain.value = false;
  values.value = empty();
  errors.value = {};
  createError.value = "";
  typeOpen.value = false;
  context.search.reset();
  creation.reset();
}
watch(identity, clearCreation, { flush: "sync" });
function showCreate(): void {
  if (
    !context.ready.value ||
    busy.value ||
    !!deletion.target.value ||
    forbidden.value
  )
    return;
  clearCreation();
  values.value = {
    ...empty(),
    contentUom: context.currentParent.value?.baseUom ?? "",
  };
  createOpen.value = true;
}
function closeCreate(): void {
  if (!pending.value) clearCreation();
}
function change(value: ItemPackagingValues): void {
  if (pending.value || uncertain.value) return;
  values.value = value;
  errors.value = {};
  createError.value = "";
}
function edit(id: string): void {
  if (busy.value || deletion.target.value) return;
  void router.push(itemPackagingEditLocation(itemId.value, id, route.fullPath));
}
function back(): void {
  void router.push(
    itemPackagingsReturnPath(itemId.value, route.query.returnTo),
  );
}
function refresh(): void {
  if (!scope.ready.value || busy.value) return;
  void readList();
  context.retry();
}
async function create(): Promise<void> {
  if (
    !createOpen.value ||
    !context.canSubmit.value ||
    busy.value ||
    !!deletion.target.value ||
    uncertain.value ||
    forbidden.value
  )
    return;
  errors.value = validateItemPackaging(
    values.value,
    context.compatibleUoms.value,
  );
  if (Object.keys(errors.value).length) return;
  const captured = identity.value,
    returnTo = route.fullPath,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  createError.value = "";
  try {
    const result = await creation.mutateAsync({
      itemId: itemId.value,
      scope: [...scope.key.value],
      values: { ...values.value },
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== identity.value) return;
    request = null;
    pending.value = false;
    createOpen.value = false;
    void router.push(
      itemPackagingEditLocation(itemId.value, result.id, returnTo),
    );
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    uncertain.value =
      !(cause instanceof ItemPackagingRequestError) || cause.uncertain;
    errors.value =
      cause instanceof ItemPackagingRequestError ? cause.fields : {};
    createError.value = uncertain.value
      ? "Результат создания не подтверждён. Проверьте точное совпадение кода в списке перед новой попыткой."
      : cause instanceof Error
        ? cause.message
        : "Не удалось создать упаковку.";
    if (
      cause instanceof ItemPackagingRequestError &&
      [409, 422].includes(cause.status ?? 0)
    ) {
      context.retrySelected();
      context.retry();
    }
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
  request?.abort();
  window.removeEventListener("beforeunload", beforeUnload);
});
const error = computed(
  () => context.error.value || query.error.value?.message || "",
);
const loading = computed(
  () =>
    !error.value && (query.isPending.value || context.parent.isPending.value),
);
const refreshing = computed(() => query.isFetching.value && !!query.data.value);
const outOfRange = computed(
  () => state.params.value.page > 1 && query.data.value?.items.length === 0,
);
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto"
    aria-label="Упаковки SKU"
  >
    <ItemPackagingsHeader
      :refreshing="query.isFetching.value"
      :disabled="query.isFetching.value || !scope.ready.value || busy"
      :create-disabled="
        !context.ready.value || busy || !!deletion.target.value || forbidden
      "
      :pending="busy"
      @back="back"
      @refresh="refresh"
      @create="showCreate"
    />
    <p v-if="notice" role="status" class="text-sm text-muted-foreground">
      {{ notice }}
    </p>
    <Alert v-if="deletion.blocked.value" variant="destructive"
      ><AlertDescription>{{ deletion.error.value }}</AlertDescription></Alert
    >
    <ItemPackagingContext
      :item="deletion.blocked.value ? undefined : context.currentParent.value"
      :loading="context.parent.isPending.value"
      :error="context.error.value"
      :pending="
        context.parent.isFetching.value ||
        context.units.isFetching.value ||
        busy
      "
      :can-retry="scope.ready.value && !busy"
      @retry="context.retry"
    />
    <ItemPackagingsToolbar
      :disabled="busy || !!deletion.target.value"
      :search="state.searchText.value"
      :total="forbidden ? undefined : query.data.value?.total"
      @search="state.setSearch"
      @submit="state.submitSearch"
      @clear="state.clearSearch"
    />
    <ItemPackagingsBody
      :disabled="
        busy || !!deletion.target.value || !context.currentParent.value
      "
      :items="forbidden ? [] : (query.data.value?.items ?? [])"
      :loading="loading"
      :refreshing="refreshing"
      :error="context.error.value ? '' : (query.error.value?.message ?? '')"
      :can-retry="scope.ready.value"
      :retry-pending="query.isFetching.value || busy"
      :filtered="!!state.params.value.search"
      :out-of-range="outOfRange"
      @retry="refresh"
      @edit="edit"
      @delete="showDelete"
      @clear="state.clearFilters"
      @first-page="state.firstPage"
    />
    <ItemPackagingsFooter
      v-if="query.data.value && !outOfRange && !forbidden"
      :page="state.params.value.page"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :disabled="query.isFetching.value || busy || !!deletion.target.value"
      @change="state.setPagination"
    />
    <DeleteItemPackagingDialog
      v-if="deletion.target.value"
      :item="deletion.target.value"
      :sku="context.currentParent.value?.sku"
      :pending="deletion.pending.value"
      :uncertain="deletion.uncertain.value"
      :error="deletion.error.value"
      @close="deletion.close"
      @confirm="deletion.confirm"
      @check="deletion.check"
    />
    <CreateItemPackagingDialog
      :open="createOpen"
      :values="values"
      :errors="errors"
      :uoms="context.compatibleUoms.value"
      :picker="context.picker.value"
      :pending="pending"
      :disabled="!context.ready.value"
      :can-submit="context.canSubmit.value"
      :uncertain="uncertain"
      :error="createError"
      @change="change"
      @submit="create"
      @close="closeCreate"
      @check="checkCreated"
      @type-search="context.search.search.value = $event"
      @type-open="typeOpen = $event"
      @type-more="context.search.more"
      @type-retry="context.search.retry"
      @type-retry-selected="context.retrySelected"
    />
  </section>
</template>
