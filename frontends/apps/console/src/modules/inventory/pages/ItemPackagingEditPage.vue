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
import { toast } from "vue-sonner";
import { useItemPackagingDeletion } from "../model/use-item-packaging-deletion";
import DeleteItemPackagingDialog from "../ui/forms/DeleteItemPackagingDialog.vue";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useItemPackagingQuery } from "../model/use-item-packaging-query";
import { useUpdateItemPackaging } from "../model/use-update-item-packaging";
import { useItemPackagingDraft } from "../model/use-item-packaging-draft";
import { useItemPackagingFormContext } from "../model/use-item-packaging-form-context";
import { itemPackagingSnapshot } from "../model/item-packaging-draft";
import { validateItemPackaging } from "../model/item-packaging.validation";
import { ItemPackagingRequestError } from "../model/item-packaging.errors";
import { itemPackagingReturnPath } from "../model/item-packaging-navigation";
import type {
  ItemPackagingValues,
  ItemPackagingErrors,
} from "../model/item-packaging.types";
import ItemPackagingEditHeader from "../ui/page/ItemPackagingEditHeader.vue";
import ItemPackagingEditBody from "../ui/results/ItemPackagingEditBody.vue";
import ItemPackagingContext from "../ui/results/ItemPackagingContext.vue";
import ItemPackagingForm from "../ui/forms/ItemPackagingForm.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const itemId = computed(() =>
    String(route.params.inventoryItemId ?? "").toLowerCase(),
  ),
  id = computed(() => String(route.params.packagingId ?? "").toLowerCase());
const identity = computed(() =>
  JSON.stringify([
    ...scope.key.value,
    scope.ready.value,
    itemId.value,
    id.value,
  ]),
);
const item = useItemPackagingQuery(itemId, id, scope),
  mutation = useUpdateItemPackaging(itemId, id, scope),
  saving = ref(false),
  typeOpen = ref(false);
const deletion = useItemPackagingDeletion(
  itemId,
  identity,
  scope,
  afterRemoval,
);
const busy = computed(() => saving.value || deletion.pending.value);
function afterRemoval(alreadyGone: boolean): void {
  draft.clear();
  clearSave();
  toast.success(alreadyGone ? "Упаковка уже удалена." : "Упаковка удалена.");
  back();
}
function showDelete(): void {
  if (
    busy.value ||
    !currentItem.value ||
    !context.currentParent.value ||
    context.parentMissing.value ||
    deletion.blocked.value
  )
    return;
  deletion.open(currentItem.value);
}
const missing = computed(
  () =>
    item.error.value instanceof ItemPackagingRequestError &&
    [403, 404].includes(item.error.value.status ?? 0),
);
const currentItem = computed(() =>
  scope.ready.value &&
  !missing.value &&
  !deletion.blocked.value &&
  deletion.removedId.value !== id.value &&
  item.data.value?.id === id.value &&
  item.data.value.inventoryItemId === itemId.value
    ? item.data.value
    : undefined,
);
const errors = ref<ItemPackagingErrors>({}),
  saveError = ref(""),
  saved = ref(false);
let request: AbortController | null = null;
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
    typeOpen.value = false;
    clearSave();
  },
  { flush: "sync" },
);
const draft = useItemPackagingDraft(() => currentItem.value, identity, busy);
const typeId = computed(() => draft.values.value?.packagingTypeId ?? "");
const context = useItemPackagingFormContext(
  itemId,
  typeId,
  typeOpen,
  identity,
  scope,
);
const unavailable = computed(
  () =>
    !!deletion.target.value ||
    !context.ready.value ||
    !currentItem.value ||
    missing.value ||
    context.parentMissing.value,
);
const readError = computed(() =>
  deletion.blocked.value
    ? deletion.error.value
    : scope.error.value || item.error.value?.message || "",
);
const loading = computed(
  () =>
    !readError.value &&
    !currentItem.value &&
    deletion.removedId.value !== id.value,
);
function change(value: ItemPackagingValues): void {
  if (deletion.target.value || deletion.removedId.value === id.value) return;
  draft.change(value);
  clearSave();
}
function reset(): void {
  if (!busy.value && !deletion.target.value) {
    draft.reset();
    clearSave();
  }
}
async function save(): Promise<void> {
  if (
    unavailable.value ||
    !context.canSubmit.value ||
    busy.value ||
    !!deletion.target.value ||
    !draft.dirty.value ||
    !draft.values.value
  )
    return;
  clearSave();
  errors.value = validateItemPackaging(
    draft.values.value,
    context.compatibleUoms.value,
  );
  if (Object.keys(errors.value).length) return;
  const changes = { ...draft.changes.value },
    sent = itemPackagingSnapshot(draft.values.value),
    captured = identity.value,
    controller = new AbortController();
  request = controller;
  saving.value = true;
  try {
    const result = await mutation.mutateAsync({
      itemId: itemId.value,
      id: id.value,
      scope: [...scope.key.value],
      values: changes,
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== identity.value) return;
    draft.acknowledge(sent, result);
    saved.value = true;
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    saveError.value =
      cause instanceof Error ? cause.message : "Не удалось сохранить упаковку.";
    if (cause instanceof ItemPackagingRequestError) {
      errors.value = Object.fromEntries(
        Object.entries(cause.fields).filter(([field]) => {
          if (
            field !== "packagingTypeId" &&
            field !== "code" &&
            field !== "name" &&
            field !== "contentQuantity" &&
            field !== "contentUom"
          )
            return false;
          return draft.values.value?.[field] === sent[field];
        }),
      );
      if ([409, 422].includes(cause.status ?? 0)) {
        if (draft.values.value?.packagingTypeId === sent.packagingTypeId)
          context.retrySelected();
        context.retry();
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
  if (!scope.ready.value || busy.value) return;
  void item.refetch();
  context.retry();
  context.retrySelected();
}
function canLeave(): boolean {
  return (
    !busy.value &&
    (!draft.dirty.value ||
      window.confirm(
        "Есть несохранённые изменения упаковки. Отказаться от изменений?",
      ))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) =>
    !busy.value &&
    ((to.params.inventoryItemId === from.params.inventoryItemId &&
      to.params.packagingId === from.params.packagingId) ||
      canLeave()),
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
function back(): void {
  void router.push(itemPackagingReturnPath(itemId.value, route.query.returnTo));
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Редактирование упаковки"
  >
    <ItemPackagingEditHeader
      :code="currentItem?.code"
      :pending="busy"
      :delete-disabled="
        !currentItem ||
        !context.currentParent.value ||
        context.parentMissing.value ||
        deletion.blocked.value
      "
      @delete="showDelete"
      @back="back"
    />
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
    <DeleteItemPackagingDialog
      v-if="deletion.target.value"
      :item="deletion.target.value"
      :sku="context.currentParent.value?.sku"
      :dirty="draft.dirty.value"
      :pending="deletion.pending.value"
      :uncertain="deletion.uncertain.value"
      :error="deletion.error.value"
      @close="deletion.close"
      @confirm="deletion.confirm"
      @check="deletion.check"
    />
    <Card class="w-full max-w-4xl shrink-0"
      ><CardHeader
        ><CardTitle>Параметры упаковки</CardTitle
        ><CardDescription
          >Количество и единица задают содержимое одного варианта
          упаковки.</CardDescription
        ></CardHeader
      ><CardContent>
        <ItemPackagingEditBody
          :loading="loading"
          :error="readError"
          :can-retry="
            scope.ready.value && !missing && !deletion.blocked.value && !busy
          "
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
                : "Упаковка сохранена."
            }}
          </p>
          <ItemPackagingForm
            v-if="
              currentItem && draft.values.value && !context.parentMissing.value
            "
            :values="draft.values.value"
            :errors="errors"
            :uoms="context.compatibleUoms.value"
            :picker="context.picker.value"
            :pending="saving"
            :disabled="unavailable"
            :can-submit="context.canSubmit.value"
            :dirty="draft.dirty.value"
            @change="change"
            @submit="save"
            @reset="reset"
            @type-search="context.search.search.value = $event"
            @type-open="typeOpen = $event"
            @type-more="context.search.more"
            @type-retry="context.search.retry"
            @type-retry-selected="context.retrySelected"
          />
        </ItemPackagingEditBody> </CardContent
    ></Card>
  </section>
</template>
