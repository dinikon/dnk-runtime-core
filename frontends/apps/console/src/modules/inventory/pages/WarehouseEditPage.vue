<script setup lang="ts">
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
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
import { useUpdateWarehouse } from "../model/use-update-warehouse";
import { useWarehouseDraft } from "../model/use-warehouse-draft";
import { warehouseSnapshot } from "../model/warehouse-draft";
import { validateWarehouse } from "../model/warehouse-form.validation";
import { WarehouseRequestError } from "../model/warehouse.errors";
import { warehouseReturnPath } from "../model/warehouse-navigation";
import { stockLocationsLocation } from "../model/stock-location-navigation";
import type {
  WarehouseEditValues,
  WarehouseFieldErrors,
} from "../model/warehouse.types";
import WarehouseEditHeader from "../ui/page/WarehouseEditHeader.vue";
import WarehouseEditBody from "../ui/results/WarehouseEditBody.vue";
import WarehouseForm from "../ui/forms/WarehouseForm.vue";
import { useStockLocationQuery } from "../model/use-stock-location-query";
import { useDefaultStorageLocationSearch } from "../model/use-default-storage-location-search";
import { useSetWarehouseDefaultStorage } from "../model/use-set-warehouse-default-storage";
import {
  DefaultStorageLocationDraft,
  isDefaultStorageCandidate,
} from "../model/default-storage-location-draft";
import { WarehouseDefaultStorageRequestError } from "../model/warehouse-default-storage.errors";
import WarehouseDefaultStorageCard from "../ui/results/WarehouseDefaultStorageCard.vue";
import SetWarehouseDefaultStorageDialog from "../ui/forms/SetWarehouseDefaultStorageDialog.vue";
import DefaultStorageLocationPicker from "../ui/forms/DefaultStorageLocationPicker.vue";

const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() => String(route.params.warehouseId ?? "").toLowerCase());
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const item = useWarehouseQuery(id, scope);
const mutation = useUpdateWarehouse(scope);
const saving = ref(false);
const assigning = ref(false);
const checkingAssignment = ref(false);
const busy = computed(
  () => saving.value || assigning.value || checkingAssignment.value,
);
const missing = computed(
  () =>
    item.error.value instanceof WarehouseRequestError &&
    [403, 404].includes(item.error.value.status ?? 0),
);
const currentItem = computed(() =>
  scope.ready.value && !missing.value && item.data.value?.id === id.value
    ? item.data.value
    : undefined,
);
const assignment = useSetWarehouseDefaultStorage(id, scope);
const assignmentOpen = ref(false);
const assignmentDraft = reactive(new DefaultStorageLocationDraft());
const assignmentError = ref("");
const assignmentFieldError = ref("");
const assignmentUncertain = ref(false);
const assignmentSaved = ref(false);
const currentLocationId = computed(
  () => currentItem.value?.defaultStorageLocationId ?? null,
);
const currentLocation = useStockLocationQuery(id, currentLocationId, scope);
const selectedLocationId = computed(() =>
  assignmentOpen.value ? assignmentDraft.selectedId : null,
);
const selectedLocation = useStockLocationQuery(id, selectedLocationId, scope);
const candidates = useDefaultStorageLocationSearch(
  id,
  assignmentOpen,
  scope,
  identity,
);
let assignmentRequest: AbortController | null = null;
const canSetDefault = computed(
  () =>
    scope.ready.value &&
    !!currentItem.value &&
    !item.error.value &&
    !busy.value,
);
const canAssign = computed(
  () =>
    canSetDefault.value &&
    !assignmentUncertain.value &&
    !!assignmentDraft.selectedId &&
    assignmentDraft.selectedId !== currentLocationId.value &&
    !selectedLocation.error.value &&
    selectedLocation.data.value?.id === assignmentDraft.selectedId &&
    isDefaultStorageCandidate(selectedLocation.data.value, id.value),
);
watch(currentLocationId, (value) => {
  if (assignmentOpen.value && !assigning.value) assignmentDraft.receive(value);
});
function clearAssignment(): void {
  assignmentRequest?.abort();
  assignmentRequest = null;
  assignmentOpen.value = false;
  assigning.value = false;
  checkingAssignment.value = false;
  assignmentDraft.reset(null);
  assignmentError.value = "";
  assignmentFieldError.value = "";
  assignmentUncertain.value = false;
  assignmentSaved.value = false;
  assignment.reset();
  candidates.reset();
}
function openAssignment(): void {
  if (!canSetDefault.value) return;
  clearAssignment();
  assignmentDraft.reset(currentLocationId.value);
  assignmentOpen.value = true;
}
function closeAssignment(): void {
  if (!assigning.value && !checkingAssignment.value) clearAssignment();
}
function selectLocation(value: string): void {
  if (busy.value || assignmentUncertain.value) return;
  assignmentDraft.change(value);
  assignmentFieldError.value = "";
  assignmentError.value = "";
}
function retryCurrentLocation(): void {
  if (scope.ready.value && currentLocationId.value && !busy.value)
    void currentLocation.refetch();
}
function retrySelectedLocation(): void {
  if (scope.ready.value && selectedLocationId.value && !busy.value)
    void selectedLocation.refetch();
}
async function checkAssignment(): Promise<void> {
  if (!assignmentOpen.value || !scope.ready.value || busy.value) return;
  const captured = identity.value;
  checkingAssignment.value = true;
  try {
    const result = await item.refetch();
    if (captured !== identity.value || !assignmentOpen.value) return;
    if (result.error) {
      assignmentError.value = result.error.message;
      return;
    }
    assignmentUncertain.value = false;
    assignmentError.value = "";
    if (selectedLocationId.value) void selectedLocation.refetch();
    candidates.retry();
  } finally {
    if (captured === identity.value) checkingAssignment.value = false;
  }
}
async function assignDefault(): Promise<void> {
  if (!assignmentOpen.value || !canAssign.value || !assignmentDraft.selectedId)
    return;
  const captured = identity.value;
  const controller = new AbortController();
  assignmentRequest = controller;
  assigning.value = true;
  assignmentError.value = "";
  assignmentFieldError.value = "";
  try {
    await assignment.mutateAsync({
      warehouseId: id.value,
      scope: [...scope.key.value],
      values: { locationId: assignmentDraft.selectedId },
      signal: controller.signal,
    });
    if (captured !== identity.value || controller.signal.aborted) return;
    assignmentOpen.value = false;
    assignmentSaved.value = true;
  } catch (cause: unknown) {
    if (captured !== identity.value || controller.signal.aborted) return;
    assignmentUncertain.value =
      !(cause instanceof WarehouseDefaultStorageRequestError) ||
      cause.uncertain;
    assignmentError.value = assignmentUncertain.value
      ? "Результат назначения не подтверждён. Проверьте текущее назначение перед повторной попыткой."
      : cause instanceof Error
        ? cause.message
        : "Не удалось назначить локацию.";
    assignmentFieldError.value =
      cause instanceof WarehouseDefaultStorageRequestError
        ? (cause.fields.locationId ?? "")
        : "";
    if (!assignmentUncertain.value) {
      void item.refetch();
      void selectedLocation.refetch();
      candidates.retry();
    }
  } finally {
    if (assignmentRequest === controller) {
      assignmentRequest = null;
      assigning.value = false;
    }
  }
}
let request: AbortController | null = null;
const errors = ref<WarehouseFieldErrors>({}),
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
    clearAssignment();
  },
  { flush: "sync" },
);
const draft = useWarehouseDraft(() => currentItem.value, identity, busy);
const readError = computed(
  () => scope.error.value || item.error.value?.message || "",
);
const unavailable = computed(
  () => !scope.ready.value || !currentItem.value || missing.value,
);
const loading = computed(() => !readError.value && !currentItem.value);
function change(value: WarehouseEditValues): void {
  draft.change(value);
  clearSave();
}
function reset(): void {
  if (!busy.value) {
    draft.reset();
    clearSave();
  }
}
async function save(): Promise<void> {
  if (
    unavailable.value ||
    busy.value ||
    !draft.dirty.value ||
    !draft.values.value
  )
    return;
  clearSave();
  errors.value = validateWarehouse(draft.values.value);
  if (Object.keys(errors.value).length) return;
  const changes = { ...draft.changes.value };
  const sent = warehouseSnapshot(draft.values.value),
    captured = identity.value;
  const controller = new AbortController();
  request = controller;
  saving.value = true;
  try {
    const result = await mutation.mutateAsync({
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
      cause instanceof Error ? cause.message : "Не удалось сохранить склад.";
    if (cause instanceof WarehouseRequestError)
      errors.value = Object.fromEntries(
        Object.entries(cause.fields).filter(([field]) => {
          const key = field as keyof WarehouseEditValues;
          return draft.values.value?.[key] === sent[key];
        }),
      );
  } finally {
    if (request === controller) {
      request = null;
      saving.value = false;
    }
  }
}
function retry(): void {
  if (!scope.ready.value || busy.value) return;
  void item.refetch();
}
function canLeave(): boolean {
  if (busy.value) return false;
  return (
    (!draft.dirty.value && !(assignmentOpen.value && assignmentDraft.dirty)) ||
    window.confirm(
      "Есть несохранённые изменения склада. Отказаться от изменений?",
    )
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) => to.params.warehouseId === from.params.warehouseId || canLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (
    draft.dirty.value ||
    (assignmentOpen.value && assignmentDraft.dirty) ||
    busy.value
  ) {
    event.preventDefault();
    event.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => {
  request?.abort();
  assignmentRequest?.abort();
  window.removeEventListener("beforeunload", beforeUnload);
});
function back(): void {
  void router.push(warehouseReturnPath(route.query.returnTo));
}
function locations(): void {
  void router.push(stockLocationsLocation(id.value, route.fullPath));
}
</script>

<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Редактирование склада"
  >
    <WarehouseEditHeader
      :code="currentItem?.code"
      :pending="busy"
      :locations-disabled="!currentItem"
      @back="back"
      @locations="locations"
    />
    <Card class="w-full max-w-4xl shrink-0">
      <CardHeader>
        <CardTitle>Параметры склада</CardTitle>
        <CardDescription>Код, название и активность склада.</CardDescription>
      </CardHeader>
      <CardContent>
        <WarehouseEditBody
          :loading="loading"
          :error="readError"
          :can-retry="scope.ready.value && !missing"
          :retry-pending="item.isFetching.value || busy"
          :refreshing="!!currentItem && item.isFetching.value"
          @retry="retry"
        >
          <Alert v-if="saveError" variant="destructive"
            ><AlertDescription>{{ saveError }}</AlertDescription></Alert
          >
          <p v-if="saved" role="status" class="text-sm text-muted-foreground">
            {{
              draft.dirty.value
                ? "Отправленные изменения сохранены. Есть новые правки."
                : "Склад сохранён."
            }}
          </p>
          <WarehouseForm
            v-if="currentItem && draft.values.value"
            :values="draft.values.value"
            :errors="errors"
            :dirty="draft.dirty.value"
            :pending="saving"
            :save-blocked="assigning || checkingAssignment"
            :disabled="unavailable"
            @change="change"
            @submit="save"
            @reset="reset"
          />
        </WarehouseEditBody>
      </CardContent>
    </Card>
    <WarehouseDefaultStorageCard
      v-if="currentItem"
      :location-id="currentLocationId"
      :location="currentLocation.data.value"
      :loading="currentLocation.isFetching.value"
      :error="currentLocation.error.value?.message || ''"
      :disabled="!canSetDefault"
      :saved="assignmentSaved"
      @change="openAssignment"
      @retry="retryCurrentLocation"
    />
    <SetWarehouseDefaultStorageDialog
      :open="assignmentOpen"
      :pending="assigning"
      :can-submit="canAssign"
      :error="assignmentError"
      :field-error="assignmentFieldError"
      :uncertain="assignmentUncertain"
      :checking="checkingAssignment"
      @close="closeAssignment"
      @submit="assignDefault"
      @check="checkAssignment"
    >
      <DefaultStorageLocationPicker
        :search="candidates.search.value"
        :options="candidates.options.value"
        :total="candidates.total.value"
        :loading="candidates.loading.value"
        :fetching-more="candidates.fetchingMore.value"
        :has-more="candidates.hasMore.value"
        :error="candidates.error.value"
        :selected-id="assignmentDraft.selectedId"
        :selected="selectedLocation.data.value"
        :selected-loading="selectedLocation.isFetching.value"
        :selected-error="selectedLocation.error.value?.message || ''"
        :disabled="busy || assignmentUncertain"
        :invalid="!!assignmentFieldError"
        @search="candidates.search.value = $event"
        @select="selectLocation"
        @more="candidates.more"
        @retry="candidates.retry"
        @retry-selected="retrySelectedLocation"
      />
    </SetWarehouseDefaultStorageDialog>
  </section>
</template>
