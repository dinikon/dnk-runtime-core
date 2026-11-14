<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { toast } from "vue-sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
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
import { useUpdateInventoryItem } from "../model/use-update-inventory-item";
import { useInventoryItemEditorDraft } from "../model/use-inventory-item-editor-draft";
import { useInventoryItemDeletion } from "../model/use-inventory-item-deletion";
import { inventoryItemEditSnapshot } from "../model/inventory-item-editor-draft";
import { inventorySettingsFields } from "../model/inventory-item-settings-draft";
import {
  emptyInventoryItemErrors,
  validateInventoryItemEditor,
  inventoryItemErrorsForSnapshot,
} from "../model/inventory-item-editor.validation";
import { InventoryItemWriteError } from "../model/inventory-item-write.errors";
import { InventorySettingsRequestError } from "../model/inventory-item-settings.errors";
import { itemPackagingsLocation } from "../model/item-packaging-navigation";
import {
  inventoryItemReturnPath,
  inventoryItemListReturnPath,
} from "../model/inventory-item-navigation";
import type {
  InventoryItemEditValues,
  InventoryItemEditErrors,
} from "../model/inventory-item-editor.types";
import { stockLotsLocation } from "../model/stock-lot-navigation";
import InventoryItemEditHeader from "../ui/page/InventoryItemEditHeader.vue";
import InventoryItemEditBody from "../ui/results/InventoryItemEditBody.vue";
import InventoryItemEditorForm from "../ui/forms/InventoryItemEditorForm.vue";
import DeleteInventoryItemDialog from "../ui/forms/DeleteInventoryItemDialog.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  String(route.params.inventoryItemId ?? "").toLowerCase(),
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const item = useInventoryItemQuery(id, scope),
  uoms = useInventoryUomsQuery(scope),
  mutation = useUpdateInventoryItem(id, scope);
const saving = ref(false),
  checking = ref(false),
  uncertain = ref(false),
  writeBlocked = ref("");
const deletion = useInventoryItemDeletion(identity, scope, afterRemoval);
const busy = computed(
  () => saving.value || checking.value || deletion.pending.value,
);
const missing = computed(
  () =>
    item.error.value instanceof InventorySettingsRequestError &&
    [403, 404].includes(item.error.value.status ?? 0),
);
const currentItem = computed(() =>
  scope.ready.value &&
  !missing.value &&
  !writeBlocked.value &&
  !deletion.blocked.value &&
  deletion.removedId.value !== id.value &&
  item.data.value?.id === id.value
    ? item.data.value
    : undefined,
);
const errors = ref<InventoryItemEditErrors>(emptyInventoryItemErrors()),
  saveError = ref(""),
  notice = ref("");
let request: AbortController | null = null;
function clearSave(): void {
  errors.value = emptyInventoryItemErrors();
  saveError.value = "";
  notice.value = "";
}
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    mutation.reset();
    saving.value = false;
    checking.value = false;
    uncertain.value = false;
    writeBlocked.value = "";
    clearSave();
  },
  { flush: "sync" },
);
const draft = useInventoryItemEditorDraft(
  () => currentItem.value,
  identity,
  busy,
);
const currentUoms = computed(() =>
  uoms.error.value instanceof InventorySettingsRequestError &&
  [403, 404].includes(uoms.error.value.status ?? 0)
    ? []
    : (uoms.data.value ?? []),
);
const settingsChanged = computed(() =>
  inventorySettingsFields.some(
    (field) => draft.changes.value[field] !== undefined,
  ),
);
const unavailable = computed(
  () => !scope.ready.value || !currentItem.value || !!deletion.target.value,
);
const readError = computed(
  () =>
    writeBlocked.value ||
    (deletion.blocked.value ? deletion.error.value : "") ||
    scope.error.value ||
    item.error.value?.message ||
    uoms.error.value?.message ||
    "",
);
const loading = computed(
  () =>
    !readError.value &&
    !currentItem.value &&
    deletion.removedId.value !== id.value,
);
function clearInputErrors(): void {
  errors.value = emptyInventoryItemErrors();
  notice.value = "";
  if (!uncertain.value) saveError.value = "";
}
function change(value: InventoryItemEditValues): void {
  if (unavailable.value) return;
  draft.change(value);
  clearInputErrors();
}
function addBarcode(): void {
  if (unavailable.value) return;
  draft.addBarcode();
  clearInputErrors();
}
function reset(): void {
  if (!busy.value && !deletion.target.value && !uncertain.value) {
    draft.reset();
    clearSave();
  }
}
async function save(): Promise<void> {
  if (
    unavailable.value ||
    busy.value ||
    uncertain.value ||
    !draft.dirty.value ||
    !draft.values.value
  )
    return;
  clearSave();
  errors.value = validateInventoryItemEditor(
    draft.values.value,
    currentUoms.value,
    settingsChanged.value,
  );
  if (
    Object.keys(errors.value.fields).length ||
    Object.keys(errors.value.barcodeRows).length
  )
    return;
  const sent = inventoryItemEditSnapshot(draft.values.value),
    changes = { ...draft.changes.value },
    captured = identity.value,
    controller = new AbortController();
  request = controller;
  saving.value = true;
  try {
    const result = await mutation.mutateAsync({
      id: id.value,
      scope: [...scope.key.value],
      changes,
      signal: controller.signal,
    });
    if (captured !== identity.value || controller.signal.aborted) return;
    draft.acknowledge(sent, result);
    notice.value = "Карточка сохранена.";
  } catch (cause: unknown) {
    if (captured !== identity.value || controller.signal.aborted) return;
    uncertain.value =
      !(cause instanceof InventoryItemWriteError) || cause.uncertain;
    saveError.value = uncertain.value
      ? "Результат сохранения не подтверждён. Проверьте карточку перед новой записью. Ваш ввод сохранён."
      : cause instanceof Error
        ? cause.message
        : "Не удалось сохранить карточку.";
    if (cause instanceof InventoryItemWriteError) {
      if (draft.values.value)
        errors.value = inventoryItemErrorsForSnapshot(
          cause,
          sent,
          draft.values.value,
        );
      if ([403, 404].includes(cause.status ?? 0))
        writeBlocked.value = cause.message;
    }
  } finally {
    if (request === controller) {
      request = null;
      saving.value = false;
    }
  }
}
async function checkSaved(): Promise<void> {
  if (!scope.ready.value || busy.value || !uncertain.value) return;
  const captured = identity.value;
  checking.value = true;
  try {
    const result = await item.refetch({ throwOnError: false });
    if (captured !== identity.value) return;
    if (result.isSuccess && result.data) {
      draft.rebase(result.data);
      uncertain.value = false;
      saveError.value = "";
      notice.value =
        "Карточка проверена. Ваш ввод сохранён; проверьте отличия перед сохранением.";
    } else
      saveError.value =
        "Не удалось проверить результат сохранения. Повторите проверку. Ваш ввод сохранён.";
  } finally {
    if (captured === identity.value) checking.value = false;
  }
}
function retry(): void {
  if (scope.ready.value && !busy.value)
    void Promise.all([item.refetch(), uoms.refetch()]);
}
function showDelete(): void {
  if (!currentItem.value || busy.value || uncertain.value) return;
  deletion.open(currentItem.value);
}
function afterRemoval(alreadyGone: boolean): void {
  draft.clear();
  clearSave();
  toast.success(
    alreadyGone
      ? "Складская позиция уже удалена."
      : "Складская позиция удалена.",
  );
  const target = router.resolve(
    inventoryItemListReturnPath(route.query.returnTo),
  );
  void router.push({
    path: target.path,
    query: target.query,
    hash: target.hash,
    state: { inventoryItemDeletionScope: JSON.stringify(scope.key.value) },
  });
}
function canLeave(): boolean {
  return (
    !busy.value &&
    (!draft.dirty.value ||
      window.confirm(
        "Есть несохранённые изменения карточки SKU. Отказаться от изменений?",
      ))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) =>
    !busy.value &&
    (to.params.inventoryItemId === from.params.inventoryItemId || canLeave()),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (draft.dirty.value || busy.value) {
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
  if (!unavailable.value && !busy.value)
    void router.push(itemPackagingsLocation(id.value, route.fullPath));
}
function lots(): void {
  if (!unavailable.value && !busy.value)
    void router.push(stockLotsLocation(id.value, route.fullPath));
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
      :pending="busy"
      :packagings-disabled="unavailable"
      :delete-disabled="!currentItem || uncertain"
      @back="back"
      @packagings="packagings"
      @lots="lots"
      @delete="showDelete"
    />
    <DeleteInventoryItemDialog
      v-if="deletion.target.value"
      :item="deletion.target.value"
      :dirty="draft.dirty.value"
      :pending="deletion.pending.value"
      :uncertain="deletion.uncertain.value"
      :error="deletion.error.value"
      @close="deletion.close"
      @confirm="deletion.confirm"
      @check="deletion.check"
    />
    <Card class="w-full max-w-4xl shrink-0">
      <CardHeader
        ><CardTitle>Карточка складской позиции</CardTitle
        ><CardDescription
          >Код SKU, штрихкоды и настройки применяются к этой позиции, в том
          числе при её использовании в каталоге.</CardDescription
        ></CardHeader
      >
      <CardContent>
        <InventoryItemEditBody
          :loading="loading"
          :error="readError"
          :can-retry="
            scope.ready.value &&
            !missing &&
            !writeBlocked &&
            !deletion.blocked.value
          "
          :retry-pending="
            item.isFetching.value || uoms.isFetching.value || busy
          "
          :refreshing="!!currentItem && item.isFetching.value"
          @retry="retry"
        >
          <Alert v-if="saveError && !writeBlocked" variant="destructive"
            ><AlertDescription
              class="flex flex-wrap items-center justify-between gap-3"
              ><span>{{ saveError }}</span
              ><Button
                v-if="uncertain && !writeBlocked"
                type="button"
                variant="outline"
                :disabled="busy"
                @click="checkSaved"
                >Проверить карточку</Button
              ></AlertDescription
            ></Alert
          >
          <p v-if="notice" role="status" class="text-sm text-muted-foreground">
            {{ notice
            }}<template v-if="draft.dirty.value">
              Есть несохранённые изменения.</template
            >
          </p>
          <InventoryItemEditorForm
            v-if="currentItem && draft.values.value"
            :values="draft.values.value"
            :errors="errors"
            :uoms="currentUoms"
            :dirty="draft.dirty.value"
            :pending="saving || checking"
            :disabled="unavailable"
            :settings-disabled="!currentUoms.length"
            :uncertain="uncertain"
            :can-submit="
              !uncertain && (!settingsChanged || !!currentUoms.length)
            "
            @change="change"
            @add-barcode="addBarcode"
            @submit="save"
            @reset="reset"
          />
        </InventoryItemEditBody>
      </CardContent>
    </Card>
  </section>
</template>
