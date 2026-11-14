<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useSupplierScope } from "../model/use-supplier-scope";
import { useSupplierSourceQuery } from "../model/use-supplier-source-query";
import { useUpdateSupplierSource } from "../model/use-update-supplier-source";
import { useSourceDraft } from "../model/use-source-draft";
import { sourceValues, validateSource, snapshot } from "../model/source-draft";
import { SupplierSourceRequestError } from "../model/supplier-source.errors";
import type {
  SourceValues,
  SourceFieldErrors,
} from "../model/supplier-source.types";
import SupplierSourceHeader from "../ui/page/SupplierSourceHeader.vue";
import SupplierSourceBody from "../ui/results/SupplierSourceBody.vue";
const scope = useSupplierScope(),
  route = useRoute(),
  router = useRouter();
const id = computed(() =>
  typeof route.params.sourceId === "string" ? route.params.sourceId : "",
);
const query = useSupplierSourceQuery(id, scope),
  update = useUpdateSupplierSource(scope);
const pending = ref(false),
  errors = ref<SourceFieldErrors>({}),
  saveError = ref(""),
  saved = ref(false);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, id.value]),
);
const draft = useSourceDraft(
  () => (query.data.value ? sourceValues(query.data.value) : undefined),
  identity,
  pending,
);
let request: AbortController | null = null;
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    pending.value = false;
    saveError.value = "";
    errors.value = {};
    saved.value = false;
    update.reset();
  },
  { flush: "sync" },
);
function change(value: SourceValues): void {
  if (pending.value || !scope.ready.value) return;
  draft.change(value);
  errors.value = {};
  saveError.value = "";
  saved.value = false;
}
async function save(): Promise<void> {
  if (
    !draft.values.value ||
    !draft.dirty.value ||
    pending.value ||
    !scope.ready.value
  )
    return;
  errors.value = validateSource(draft.values.value);
  if (Object.keys(errors.value).length) return;
  const sent = snapshot(draft.values.value),
    captured = identity.value,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  saveError.value = "";
  saved.value = false;
  try {
    const result = await update.mutateAsync({
      id: id.value,
      changes: draft.changes.value,
      scope: [...scope.key.value],
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== identity.value) return;
    draft.acknowledge(sent, sourceValues(result));
    saved.value = true;
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    errors.value =
      cause instanceof SupplierSourceRequestError ? cause.fields : {};
    saveError.value =
      cause instanceof Error
        ? cause.message
        : "Не удалось сохранить источник. Ваш ввод сохранён.";
  } finally {
    if (request === controller) {
      request = null;
      pending.value = false;
    }
  }
}
function back(): void {
  const returnTo = route.query.returnTo;
  void router.push(
    typeof returnTo === "string" &&
      /^\/supplier-sourcing\/sources(?:\?|$)/.test(returnTo)
      ? returnTo
      : { name: "supplier-sources" },
  );
}
function canLeave(): boolean {
  return (
    !pending.value &&
    (!draft.dirty.value ||
      window.confirm("Есть несохранённые изменения. Покинуть карточку?"))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate(
  (to, from) => to.params.sourceId === from.params.sourceId || canLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (pending.value || draft.dirty.value) {
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
function reset(): void {
  draft.reset();
  errors.value = {};
  saveError.value = "";
  saved.value = false;
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Карточка источника"
  >
    <SupplierSourceHeader
      :name="query.data.value?.name"
      :pending="pending"
      @back="back"
    />
    <SupplierSourceBody
      :source="query.data.value"
      :values="draft.values.value"
      :errors="errors"
      :ready="scope.ready.value"
      :pending="pending"
      :dirty="draft.dirty.value"
      :error="error"
      :save-error="saveError"
      :saved="saved"
      :loading="query.isPending.value"
      :refreshing="query.isFetching.value"
      @change="change"
      @submit="save"
      @reset="reset"
      @retry="query.refetch()"
    />
  </section>
</template>
