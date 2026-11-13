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
import {
  useInventoryItemQuery,
  useInventoryUomsQuery,
} from "../model/use-inventory-item-query";
import { useUpdateInventoryItemSettings } from "../model/use-update-inventory-item-settings";
import { useInventoryItemSettingsDraft } from "../model/use-inventory-item-settings-draft";
import { inventorySettingsSnapshot } from "../model/inventory-item-settings-draft";
import { validateInventorySettings } from "../model/inventory-item-settings.validation";
import { InventorySettingsRequestError } from "../model/inventory-item-settings.errors";
import { itemPackagingsLocation } from "../model/item-packaging-navigation";
import { inventoryItemReturnPath } from "../model/inventory-item-navigation";
import type {
  InventoryItemSettings,
  InventorySettingsErrors,
} from "../model/inventory-item-settings.types";
import InventoryItemEditHeader from "../ui/page/InventoryItemEditHeader.vue";
import InventoryItemEditBody from "../ui/results/InventoryItemEditBody.vue";
import InventoryItemSettingsForm from "../ui/forms/InventoryItemSettingsForm.vue";

const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() => String(route.params.inventoryItemId ?? ""));
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const item = useInventoryItemQuery(id, scope),
  uoms = useInventoryUomsQuery(scope);
const mutation = useUpdateInventoryItemSettings(scope);
const saving = ref(false);
const missing = computed(
  () =>
    item.error.value instanceof InventorySettingsRequestError &&
    [403, 404].includes(item.error.value.status ?? 0),
);
const currentItem = computed(() =>
  scope.ready.value && !missing.value && item.data.value?.id === id.value
    ? item.data.value
    : undefined,
);
let request: AbortController | null = null;
const errors = ref<InventorySettingsErrors>({}),
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
const draft = useInventoryItemSettingsDraft(
  () => currentItem.value,
  identity,
  saving,
);
const readError = computed(
  () =>
    scope.error.value ||
    item.error.value?.message ||
    uoms.error.value?.message ||
    "",
);
const unavailable = computed(
  () =>
    !scope.ready.value ||
    !currentItem.value ||
    !uoms.data.value?.length ||
    missing.value,
);
const loading = computed(
  () => !readError.value && (!currentItem.value || !uoms.data.value),
);
function change(value: InventoryItemSettings): void {
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
  errors.value = validateInventorySettings(
    draft.values.value,
    uoms.data.value ?? [],
  );
  if (Object.keys(errors.value).length) return;
  const sent = inventorySettingsSnapshot(draft.values.value),
    captured = identity.value;
  const controller = new AbortController();
  request = controller;
  saving.value = true;
  try {
    const result = await mutation.mutateAsync({
      id: id.value,
      scope: [...scope.key.value],
      settings: sent,
      signal: controller.signal,
    });
    if (captured !== identity.value || controller.signal.aborted) return;
    draft.acknowledge(sent, result);
    saved.value = true;
  } catch (cause: unknown) {
    if (captured !== identity.value || controller.signal.aborted) return;
    saveError.value =
      cause instanceof Error
        ? cause.message
        : "Не удалось сохранить настройки.";
    if (cause instanceof InventorySettingsRequestError)
      errors.value = Object.fromEntries(
        Object.entries(cause.fields).filter(([field]) => {
          const key = field as keyof InventoryItemSettings;
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
  if (!scope.ready.value || saving.value) return;
  void Promise.all([item.refetch(), uoms.refetch()]);
}
function canLeave(): boolean {
  if (saving.value) return false;
  return (
    !draft.dirty.value ||
    window.confirm("Есть несохранённые настройки SKU. Отказаться от изменений?")
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) =>
    to.params.inventoryItemId === from.params.inventoryItemId || canLeave(),
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
function packagings(): void {
  if (!unavailable.value && !saving.value)
    void router.push(itemPackagingsLocation(id.value, route.fullPath));
}
function back(): void {
  void router.push(inventoryItemReturnPath(route.query.returnTo));
}
</script>

<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Редактирование складской позиции"
  >
    <InventoryItemEditHeader
      :sku="currentItem?.sku"
      :pending="saving"
      :packagings-disabled="unavailable"
      @back="back"
      @packagings="packagings"
    />
    <Card class="w-full max-w-4xl shrink-0">
      <CardHeader>
        <CardTitle>Параметры складского учёта</CardTitle>
        <CardDescription
          >Настройки применяются к этому SKU, в том числе при его использовании
          в каталоге.</CardDescription
        >
      </CardHeader>
      <CardContent>
        <InventoryItemEditBody
          :loading="loading"
          :error="readError"
          :can-retry="scope.ready.value && !missing"
          :retry-pending="
            item.isFetching.value || uoms.isFetching.value || saving
          "
          :refreshing="!!currentItem && item.isFetching.value"
          @retry="retry"
        >
          <Alert v-if="saveError" variant="destructive"
            ><AlertDescription>{{ saveError }}</AlertDescription></Alert
          >
          <p v-if="saved" role="status" class="text-sm text-muted-foreground">
            {{
              draft.dirty.value
                ? "Отправленные настройки сохранены. Есть новые изменения."
                : "Настройки сохранены."
            }}
          </p>
          <InventoryItemSettingsForm
            v-if="currentItem && draft.values.value && uoms.data.value"
            :values="draft.values.value"
            :uoms="uoms.data.value"
            :errors="errors"
            :dirty="draft.dirty.value"
            :pending="saving"
            :disabled="unavailable"
            @change="change"
            @submit="save"
            @reset="reset"
          />
        </InventoryItemEditBody>
      </CardContent>
    </Card>
  </section>
</template>
