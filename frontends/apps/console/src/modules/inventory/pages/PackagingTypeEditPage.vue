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
import { usePackagingTypeQuery } from "../model/use-packaging-type-query";
import { useUpdatePackagingType } from "../model/use-update-packaging-type";
import { usePackagingTypeDraft } from "../model/use-packaging-type-draft";
import { packagingTypeSnapshot } from "../model/packaging-type-draft";
import { validatePackagingType } from "../model/packaging-type-form.validation";
import { PackagingTypeRequestError } from "../model/packaging-type.errors";
import { packagingTypeReturnPath } from "../model/packaging-type-navigation";
import type {
  PackagingTypeEditValues,
  PackagingTypeFieldErrors,
} from "../model/packaging-type.types";
import PackagingTypeEditHeader from "../ui/page/PackagingTypeEditHeader.vue";
import PackagingTypeEditBody from "../ui/results/PackagingTypeEditBody.vue";
import PackagingTypeForm from "../ui/forms/PackagingTypeForm.vue";

const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  String(route.params.packagingTypeId ?? "").toLowerCase(),
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const item = usePackagingTypeQuery(id, scope);
const mutation = useUpdatePackagingType(id, scope);
const saving = ref(false);
const missing = computed(
  () =>
    item.error.value instanceof PackagingTypeRequestError &&
    [403, 404].includes(item.error.value.status ?? 0),
);
const currentItem = computed(() =>
  scope.ready.value && !missing.value && item.data.value?.id === id.value
    ? item.data.value
    : undefined,
);
let request: AbortController | null = null;
const errors = ref<PackagingTypeFieldErrors>({}),
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
const draft = usePackagingTypeDraft(() => currentItem.value, identity, saving);
const readError = computed(
  () => scope.error.value || item.error.value?.message || "",
);
const unavailable = computed(
  () => !scope.ready.value || !currentItem.value || missing.value,
);
const loading = computed(() => !readError.value && !currentItem.value);
function change(value: PackagingTypeEditValues): void {
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
  errors.value = validatePackagingType(draft.values.value);
  if (Object.keys(errors.value).length) return;
  const changes = { ...draft.changes.value };
  const sent = packagingTypeSnapshot(draft.values.value),
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
      cause instanceof Error ? cause.message : "Не удалось сохранить тип тары.";
    if (cause instanceof PackagingTypeRequestError)
      errors.value = Object.fromEntries(
        Object.entries(cause.fields).filter(([field]) => {
          if (field !== "code" && field !== "name" && field !== "isActive")
            return false;
          return draft.values.value?.[field] === sent[field];
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
  void item.refetch();
}
function canLeave(): boolean {
  if (saving.value) return false;
  return (
    !draft.dirty.value ||
    window.confirm(
      "Есть несохранённые изменения типа тары. Отказаться от изменений?",
    )
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) =>
    to.params.packagingTypeId === from.params.packagingTypeId || canLeave(),
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
  void router.push(packagingTypeReturnPath(route.query.returnTo));
}
</script>

<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Редактирование типа тары"
  >
    <PackagingTypeEditHeader
      :code="currentItem?.code"
      :pending="saving"
      @back="back"
    />
    <Card class="w-full max-w-4xl shrink-0">
      <CardHeader>
        <CardTitle>Параметры типа тары</CardTitle>
        <CardDescription>Код, название и активность типа тары.</CardDescription>
      </CardHeader>
      <CardContent>
        <PackagingTypeEditBody
          :loading="loading"
          :error="readError"
          :can-retry="scope.ready.value && !missing"
          :retry-pending="item.isFetching.value || saving"
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
                : "Тип тары сохранён."
            }}
          </p>
          <PackagingTypeForm
            v-if="currentItem && draft.values.value"
            :values="draft.values.value"
            :errors="errors"
            :dirty="draft.dirty.value"
            :pending="saving"
            :disabled="unavailable"
            @change="change"
            @submit="save"
            @reset="reset"
          />
        </PackagingTypeEditBody>
      </CardContent>
    </Card>
  </section>
</template>
