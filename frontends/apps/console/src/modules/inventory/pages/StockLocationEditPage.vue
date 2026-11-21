<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useWarehouseQuery } from "../model/use-warehouse-query";
import { WarehouseRequestError } from "../model/warehouse.errors";
import { useStockLocationQuery } from "../model/use-stock-location-query";
import { useUpdateStockLocation } from "../model/use-update-stock-location";
import { useStockLocationDraft } from "../model/use-stock-location-draft";
import { stockLocationSnapshot } from "../model/stock-location-draft";
import { validateStockLocation } from "../model/stock-location-form.validation";
import {
  StockLocationRequestError,
  stockLocationUnavailable,
} from "../model/stock-location.errors";
import {
  stockLocationRouteId,
  stockLocationsReturnPath,
} from "../model/stock-location-navigation";
import type {
  StockLocationEditValues,
  StockLocationFieldErrors,
} from "../model/stock-location.types";
import StockLocationEditHeader from "../ui/page/StockLocationEditHeader.vue";
import StockLocationEditBody from "../ui/results/StockLocationEditBody.vue";
import StockLocationContext from "../ui/results/StockLocationContext.vue";
import StockLocationForm from "../ui/forms/StockLocationForm.vue";

const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const warehouseId = computed(() =>
    stockLocationRouteId(route.params.warehouseId),
  ),
  id = computed(() => stockLocationRouteId(route.params.locationId));
const identity = computed(() =>
  JSON.stringify([
    ...scope.key.value,
    scope.ready.value,
    warehouseId.value,
    id.value,
  ]),
);
const warehouse = useWarehouseQuery(warehouseId, scope),
  item = useStockLocationQuery(warehouseId, id, scope);
const mutation = useUpdateStockLocation(warehouseId, id, scope),
  saving = ref(false);
const warehouseMissing = computed(
  () =>
    warehouse.error.value instanceof WarehouseRequestError &&
    [403, 404].includes(warehouse.error.value.status ?? 0),
);
const missing = computed(
  () => warehouseMissing.value || stockLocationUnavailable(item.error.value),
);
const currentWarehouse = computed(() =>
  scope.ready.value &&
  !warehouse.error.value &&
  warehouse.data.value?.id === warehouseId.value
    ? warehouse.data.value
    : undefined,
);
const currentItem = computed(() =>
  scope.ready.value &&
  !missing.value &&
  item.data.value?.id === id.value &&
  item.data.value.warehouseId === warehouseId.value
    ? item.data.value
    : undefined,
);
const parentId = computed(() => currentItem.value?.parentLocationId ?? null),
  parent = useStockLocationQuery(warehouseId, parentId, scope);
const isDefault = computed(() =>
  currentWarehouse.value && currentItem.value
    ? currentWarehouse.value.defaultStorageLocationId === currentItem.value.id
    : null,
);
let request: AbortController | null = null;
const errors = ref<StockLocationFieldErrors>({}),
  saveError = ref(""),
  saved = ref(false);
function clearSave(): void {
  errors.value = {};
  saveError.value = "";
  saved.value = false;
}
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    mutation.reset();
    saving.value = false;
    clearSave();
  },
  { flush: "sync" },
);
const draft = useStockLocationDraft(() => currentItem.value, identity, saving);
const readError = computed(
  () =>
    scope.error.value ||
    warehouse.error.value?.message ||
    item.error.value?.message ||
    "",
);
const unavailable = computed(
  () =>
    !scope.ready.value ||
    !currentWarehouse.value ||
    !currentItem.value ||
    missing.value,
);
const loading = computed(() => !readError.value && !currentItem.value);
function change(value: StockLocationEditValues): void {
  draft.change(value);
  clearSave();
}
function reset(): void {
  if (!saving.value) {
    draft.reset();
    clearSave();
  }
}
async function save(): Promise<void> {
  if (
    unavailable.value ||
    saving.value ||
    !draft.dirty.value ||
    !draft.values.value
  )
    return;
  clearSave();
  errors.value = validateStockLocation(draft.values.value);
  if (isDefault.value && !draft.values.value.isActive)
    errors.value.isActive =
      "Основную STORAGE нельзя деактивировать. Сначала требуется её переназначение.";
  if (Object.keys(errors.value).length) return;
  const changes = { ...draft.changes.value },
    sent = stockLocationSnapshot(draft.values.value),
    captured = identity.value,
    controller = new AbortController();
  request = controller;
  saving.value = true;
  try {
    const result = await mutation.mutateAsync({
      warehouseId: warehouseId.value,
      id: id.value,
      scope: [...scope.key.value],
      values: changes,
      signal: controller.signal,
    });
    if (captured !== identity.value || controller.signal.aborted) return;
    draft.acknowledge(sent, result);
    saved.value = true;
  } catch (cause: unknown) {
    if (captured !== identity.value || controller.signal.aborted) return;
    saveError.value =
      cause instanceof Error ? cause.message : "Не удалось сохранить локацию.";
    if (cause instanceof StockLocationRequestError) {
      errors.value = Object.fromEntries(
        Object.entries(cause.fields).filter(([field]) => {
          if (field !== "code" && field !== "name" && field !== "isActive")
            return false;
          return draft.values.value?.[field] === sent[field];
        }),
      );
      if (cause.status === 409) {
        void warehouse.refetch();
        void item.refetch();
      }
    }
  } finally {
    if (request === controller) {
      request = null;
      saving.value = false;
    }
  }
}
function retry(): void {
  if (scope.ready.value && !saving.value) {
    void warehouse.refetch();
    void item.refetch();
  }
}
function retryParent(): void {
  if (scope.ready.value && parentId.value) void parent.refetch();
}
function canLeave(): boolean {
  return (
    !saving.value &&
    (!draft.dirty.value ||
      window.confirm(
        "Есть несохранённые изменения локации. Отказаться от изменений?",
      ))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) =>
    (to.params.warehouseId === from.params.warehouseId &&
      to.params.locationId === from.params.locationId) ||
    canLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (draft.dirty.value || saving.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => {
  request?.abort();
  window.removeEventListener("beforeunload", beforeUnload);
});
function back(): void {
  void router.push(
    stockLocationsReturnPath(warehouseId.value, route.query.returnTo),
  );
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Редактирование локации"
  >
    <StockLocationEditHeader
      :code="currentItem?.code"
      :pending="saving"
      @back="back"
    />
    <Card class="w-full max-w-4xl shrink-0"
      ><CardHeader
        ><CardTitle>Параметры локации</CardTitle
        ><CardDescription
          >Код, название и локальная активность. Склад, родитель и тип
          сохраняются.</CardDescription
        ></CardHeader
      ><CardContent>
        <StockLocationEditBody
          :loading="loading"
          :error="readError"
          :can-retry="scope.ready.value && !missing"
          :retry-pending="
            warehouse.isFetching.value || item.isFetching.value || saving
          "
          :refreshing="
            !!currentItem &&
            (item.isFetching.value || warehouse.isFetching.value)
          "
          @retry="retry"
        >
          <template v-if="currentItem && draft.values.value">
            <StockLocationContext
              :item="currentItem"
              :warehouse="currentWarehouse"
              :parent="parent.data.value"
              :parent-loading="parent.isFetching.value"
              :parent-error="parent.error.value?.message || ''"
              :is-default="isDefault"
              @retry-parent="retryParent"
            />
            <Alert v-if="saveError" variant="destructive"
              ><AlertDescription>{{ saveError }}</AlertDescription></Alert
            >
            <p v-if="saved" role="status" class="text-sm text-muted-foreground">
              {{
                draft.dirty.value
                  ? "Отправленные изменения сохранены. Есть новые правки."
                  : "Локация сохранена."
              }}
            </p>
            <StockLocationForm
              :values="draft.values.value"
              :errors="errors"
              :dirty="draft.dirty.value"
              :pending="saving"
              :disabled="!scope.ready.value || missing"
              :save-disabled="unavailable"
              :is-default="isDefault"
              @change="change"
              @submit="save"
              @reset="reset"
            />
          </template>
        </StockLocationEditBody> </CardContent
    ></Card>
  </section>
</template>
