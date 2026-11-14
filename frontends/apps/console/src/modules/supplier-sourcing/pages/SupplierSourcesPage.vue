<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRouter,
  useRoute,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useSupplierScope } from "../model/use-supplier-scope";
import { useSourcesPageState } from "../model/use-sources-page-state";
import { useSupplierSourcesQuery } from "../model/use-supplier-sources-query";
import { useCreateSupplierSource } from "../model/use-create-supplier-source";
import { useSupplierLookup } from "../model/use-supplier-lookup";
import { emptySource } from "../model/supplier-source.constants";
import { validateSource, snapshot } from "../model/source-draft";
import { SupplierSourceRequestError } from "../model/supplier-source.errors";
import type {
  SourceValues,
  SourceFieldErrors,
} from "../model/supplier-source.types";
import type { CounterpartyReference } from "@/modules/crm";
import SupplierSourcesHeader from "../ui/page/SupplierSourcesHeader.vue";
import SupplierSourcesToolbar from "../ui/page/SupplierSourcesToolbar.vue";
import SupplierSourcesFooter from "../ui/page/SupplierSourcesFooter.vue";
import SupplierSourcesBody from "../ui/results/SupplierSourcesBody.vue";
import CreateSupplierSourceDialog from "../ui/forms/CreateSupplierSourceDialog.vue";
const scope = useSupplierScope(),
  state = useSourcesPageState(scope.key),
  router = useRouter(),
  route = useRoute();
const query = useSupplierSourcesQuery(state.params, scope),
  creation = useCreateSupplierSource(scope);
const createOpen = ref(false),
  pending = ref(false),
  uncertain = ref(false),
  values = ref<SourceValues>(emptySource()),
  errors = ref<SourceFieldErrors>({}),
  createError = ref("");
const picker = useSupplierLookup(
    scope,
    createOpen,
    computed(() => values.value.supplierModelKey),
  ),
  filter = useSupplierLookup(
    scope,
    computed(() => scope.ready.value && !!state.params.value.supplierModelKey),
    computed(() => state.params.value.supplierModelKey || "crm.company"),
  );
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
  values.value = emptySource();
  errors.value = {};
  createError.value = "";
  picker.reset();
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
function change(value: SourceValues): void {
  if (pending.value || uncertain.value) return;
  values.value = snapshot(value);
  errors.value = {};
  createError.value = "";
}
function selectCounterparty(counterparty: CounterpartyReference): void {
  picker.select(counterparty);
  change({
    ...values.value,
    supplierModelKey: counterparty.modelKey,
    supplierId: counterparty.id,
  });
}
function open(id: string): void {
  void router.push({
    name: "supplier-source",
    params: { sourceId: id },
    query: { returnTo: route.fullPath },
  });
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
  errors.value = validateSource(values.value);
  if (Object.keys(errors.value).length) return;
  const captured = identity.value,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  createError.value = "";
  try {
    const result = await creation.mutateAsync({
      values: snapshot(values.value),
      scope: [...scope.key.value],
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== identity.value) return;
    pending.value = false;
    createOpen.value = false;
    open(result.id);
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    uncertain.value =
      !(cause instanceof SupplierSourceRequestError) || cause.uncertain;
    errors.value =
      cause instanceof SupplierSourceRequestError ? cause.fields : {};
    createError.value = uncertain.value
      ? "Результат создания не подтверждён. Проверьте список перед новой попыткой."
      : cause instanceof Error
        ? cause.message
        : "Не удалось создать источник.";
  } finally {
    if (request === controller) {
      request = null;
      pending.value = false;
    }
  }
}
function checkCreated(): void {
  const search = values.value.name;
  closeCreate();
  state.change({
    search,
    page: 1,
    supplierModelKey: "",
    supplierId: "",
    activity: "all",
    fulfillmentMode: "all",
  });
  refresh();
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
const filtered = computed(
  () =>
    !!state.params.value.search ||
    !!state.params.value.supplierModelKey ||
    !!state.params.value.supplierId ||
    state.params.value.activity !== "all" ||
    state.params.value.fulfillmentMode !== "all",
);
const outOfRange = computed(
  () => state.params.value.page > 1 && query.data.value?.items.length === 0,
);
</script>
<template>
  <section
    class="flex min-w-0 flex-1 flex-col gap-5"
    aria-label="Источники поставщиков"
  >
    <SupplierSourcesHeader
      :disabled="!scope.ready.value || pending"
      :refreshing="query.isFetching.value"
      @create="showCreate"
      @refresh="refresh"
    /><SupplierSourcesToolbar
      :params="state.params.value"
      :search="state.searchText.value ?? ''"
      :total="query.data.value?.total"
      :supplier-search="filter.search.value"
      :supplier-options="filter.items.value"
      :suppliers-loading="filter.loading.value"
      :suppliers-error="filter.error.value"
      :supplier-offset="filter.params.value.offset"
      :suppliers-total="filter.total.value"
      @search="state.search"
      @change="state.change"
      @clear="state.clear"
      @supplier-search="filter.setSearch"
      @supplier-page="filter.page"
      @supplier-retry="filter.retry"
    /><SupplierSourcesBody
      :items="query.data.value?.items ?? []"
      :loading="query.isPending.value && !error"
      :refreshing="query.isFetching.value"
      :error="error"
      :can-retry="scope.ready.value"
      :filtered="filtered"
      :out-of-range="outOfRange"
      @retry="refresh"
      @clear="state.clear"
      @first="state.change({ page: 1 })"
      @open="open"
    /><SupplierSourcesFooter
      v-if="query.data.value && !outOfRange"
      :page="state.params.value.page"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :disabled="query.isFetching.value"
      @change="state.change"
    />
    <CreateSupplierSourceDialog
      :open="createOpen"
      :values="values"
      :errors="errors"
      :pending="pending"
      :disabled="!scope.ready.value"
      :error="createError"
      :uncertain="uncertain"
      :counterparty-search="picker.search.value"
      :counterparties="picker.items.value"
      :selected-counterparty="picker.selected.value"
      :counterparties-loading="picker.loading.value"
      :counterparties-error="picker.error.value"
      :counterparties-offset="picker.params.value.offset"
      :counterparties-total="picker.total.value"
      @close="closeCreate"
      @change="change"
      @submit="create"
      @check="checkCreated"
      @counterparty-search="picker.setSearch"
      @counterparty-select="selectCounterparty"
      @counterparty-page="picker.page"
      @counterparty-retry="picker.retry"
    />
  </section>
</template>
