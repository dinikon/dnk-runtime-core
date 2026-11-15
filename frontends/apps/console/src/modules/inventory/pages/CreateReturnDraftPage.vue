<script setup lang="ts">
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryUomsQuery } from "../model/use-inventory-item-query";
import { useReturnOrigin } from "../model/use-return-origin";
import { useCreateReturn } from "../model/use-create-return";
import {
  emptyReturnDraft,
  copyReturnDraft,
  validateReturnDraft,
  hasReturnErrors,
  ReturnCreationAttempt,
} from "../model/return-draft";
import { toggleReturnOrigin } from "../model/return-plan";
import {
  returnDirectionLabel,
  type ReturnOriginLine,
} from "../model/return-origin.types";
import type { ReturnDraftLine, ReturnErrors } from "../model/return.types";
import { ReturnRequestError } from "../model/return.errors";
import ReturnReasonField from "../ui/forms/ReturnReasonField.vue";
import ReturnPlanLinesForm from "../ui/forms/ReturnPlanLinesForm.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const originId = computed(() =>
  typeof route.query.origin_execution_id === "string"
    ? route.query.origin_execution_id
    : "",
);
const identity = computed(() =>
  JSON.stringify([...scope.key.value, scope.ready.value, originId.value]),
);
const origin = useReturnOrigin(originId, scope),
  uoms = useInventoryUomsQuery(scope),
  create = useCreateReturn(scope);
const values = ref({
    ...emptyReturnDraft(),
    originExecutionId: originId.value,
  }),
  errors = ref<ReturnErrors>({ lineFields: {} }),
  error = ref(""),
  pending = ref(false),
  done = ref(false),
  attempt = reactive(new ReturnCreationAttempt());
let request: AbortController | null = null;
const dirty = computed(
    () => !!values.value.reason || !!values.value.lines.length,
  ),
  disabled = computed(
    () =>
      pending.value ||
      attempt.uncertain ||
      !scope.ready.value ||
      !origin.data.value ||
      !!origin.error.value,
  );
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    values.value = { ...emptyReturnDraft(), originExecutionId: originId.value };
    errors.value = { lineFields: {} };
    error.value = "";
    pending.value = false;
    done.value = false;
    attempt.clear();
    create.reset();
  },
  { flush: "sync" },
);
function changeLine(key: string, line: ReturnDraftLine): void {
  if (disabled.value) return;
  values.value.lines = values.value.lines.map((v) =>
    v.key === key ? { ...line } : v,
  );
  errors.value = { lineFields: {} };
  error.value = "";
}
function select(line: ReturnOriginLine, selected: boolean): void {
  if (!disabled.value)
    values.value.lines = toggleReturnOrigin(
      values.value.lines,
      line,
      selected,
      () => crypto.randomUUID(),
    );
}
async function save(): Promise<void> {
  if (
    pending.value ||
    !scope.ready.value ||
    !origin.data.value ||
    origin.error.value
  )
    return;
  errors.value = validateReturnDraft(values.value);
  if (hasReturnErrors(errors.value)) return;
  const captured = identity.value,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  error.value = "";
  try {
    const sent = attempt.begin(copyReturnDraft(values.value), () =>
      crypto.randomUUID(),
    );
    const result = await create.mutateAsync({
      values: sent.values,
      key: sent.key,
      scope: [...scope.key.value],
      signal: controller.signal,
    });
    if (controller.signal.aborted || captured !== identity.value) return;
    done.value = true;
    attempt.clear();
    void router.replace({
      name: "inventory-return-document",
      params: { documentId: result.id },
    });
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    errors.value =
      cause instanceof ReturnRequestError ? cause.fields : { lineFields: {} };
    error.value =
      cause instanceof Error ? cause.message : "Не удалось создать возврат.";
    attempt.fail(
      !(cause instanceof ReturnRequestError) ||
        !cause.status ||
        cause.status >= 500,
    );
  } finally {
    if (request === controller) {
      request = null;
      pending.value = false;
    }
  }
}
function canLeave(): boolean {
  return (
    done.value ||
    (!pending.value &&
      (!dirty.value ||
        window.confirm("Есть несохранённый возврат. Покинуть страницу?")))
  );
}
onBeforeRouteLeave(canLeave);
function beforeUnload(e: BeforeUnloadEvent): void {
  if (!done.value && (dirty.value || pending.value)) {
    e.preventDefault();
    e.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => {
  request?.abort();
  window.removeEventListener("beforeunload", beforeUnload);
});
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Создание возврата"
  >
    <header class="flex flex-wrap items-start justify-between gap-3">
      <h1 class="text-2xl font-semibold">Новый возврат</h1>
      <Button
        variant="outline"
        :disabled="pending"
        @click="router.push({ name: 'inventory-return-documents' })"
        >К возвратам</Button
      >
    </header>
    <p v-if="!originId" role="alert">
      Откройте исходное исполнение поступления или расхода и выберите «Создать
      возврат».
    </p>
    <p v-else-if="origin.isPending.value" role="status">Загрузка основания…</p>
    <p
      v-if="scope.error.value || origin.error.value"
      role="alert"
      class="text-destructive"
    >
      {{ scope.error.value || origin.error.value?.message }}
      <Button variant="outline" @click="origin.refetch()"
        >Повторить загрузку основания</Button
      >
    </p>
    <form
      v-if="
        origin.data.value &&
        scope.ready.value &&
        !(
          origin.error.value instanceof ReturnRequestError &&
          [403, 404].includes(origin.error.value.status ?? 0)
        )
      "
      class="flex w-full max-w-5xl shrink-0 flex-col gap-5 rounded-lg border p-4 sm:p-6"
      @submit.prevent="save"
    >
      <p class="font-medium">
        {{ returnDirectionLabel(origin.data.value.direction) }} ·
        {{ origin.data.value.warehouseCode }} —
        {{ origin.data.value.warehouseName }}
      </p>
      <p class="break-all text-sm">
        Исходное исполнение: {{ origin.data.value.executionId }}
      </p>
      <p class="text-sm text-muted-foreground">
        Сохраняется план. Физический запас и лимит возврата пока не изменяются.
      </p>
      <ReturnReasonField
        :value="values.reason"
        :error="errors.reason"
        :disabled="disabled"
        @change="values.reason = $event"
      />
      <ReturnPlanLinesForm
        :origins="origin.data.value.lines"
        :lines="values.lines"
        :errors="errors"
        :disabled="disabled"
        :uoms="uoms.data.value ?? []"
        @select="select"
        @change="changeLine"
      />
      <p v-if="uoms.error.value" role="alert" class="text-destructive">
        {{ uoms.error.value.message
        }}<Button type="button" variant="outline" @click="uoms.refetch()"
          >Загрузить единицы</Button
        >
      </p>
      <p v-if="error" role="alert" class="text-destructive">{{ error }}</p>
      <p v-if="attempt.uncertain" role="alert">
        Ответ неизвестен. Повторите исходный запрос с прежним ключом; ввод
        сохранён.
      </p>
      <Button
        type="submit"
        class="self-start"
        :disabled="pending || !scope.ready.value || !uoms.data.value?.length"
        >{{
          pending
            ? "Создание…"
            : attempt.uncertain
              ? "Повторить исходный запрос"
              : "Сохранить черновик"
        }}</Button
      >
    </form>
  </section>
</template>
