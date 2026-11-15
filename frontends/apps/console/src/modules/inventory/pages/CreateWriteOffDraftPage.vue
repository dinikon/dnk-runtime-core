<script setup lang="ts">
import WriteOffReasonField from "../ui/forms/WriteOffReasonField.vue";
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useCreateWriteOff } from "../model/use-create-write-off";
import { useInventorySkuSearch } from "../model/use-inventory-sku-search";
import { useInventoryUomsQuery } from "../model/use-inventory-item-query";
import { useWriteOffLookups } from "../model/use-write-off-lookups";
import {
  emptyWriteOffDraft,
  newWriteOffLine,
  copyWriteOffDraft,
  validateWriteOffDraft,
  hasWriteOffErrors,
  WriteOffCreationAttempt,
} from "../model/write-off-draft";
import { WriteOffRequestError } from "../model/write-off.errors";
import type {
  WriteOffDraftLine,
  WriteOffErrors,
} from "../model/write-off.types";
import type { InventorySkuOption } from "../model/inventory-sku.types";
import WriteOffReferencePicker from "../ui/forms/WriteOffReferencePicker.vue";
import WriteOffDraftLinesForm from "../ui/forms/WriteOffDraftLinesForm.vue";
const scope = useInventoryScope(),
  router = useRouter(),
  values = ref(emptyWriteOffDraft()),
  errors = ref<WriteOffErrors>({ lineFields: {} }),
  error = ref(""),
  pending = ref(false),
  done = ref(false),
  activeKey = ref(""),
  attempt = reactive(new WriteOffCreationAttempt()),
  identity = computed(() =>
    JSON.stringify([...scope.key.value, scope.ready.value]),
  ),
  enabled = computed(() => scope.ready.value),
  lookup = useWriteOffLookups(scope, true),
  sku = useInventorySkuSearch(enabled, identity),
  uoms = useInventoryUomsQuery(scope),
  create = useCreateWriteOff(scope);
let request: AbortController | null = null;
const disabled = computed(
    () => pending.value || attempt.uncertain || !scope.ready.value,
  ),
  dirty = computed(
    () => JSON.stringify(values.value) !== JSON.stringify(emptyWriteOffDraft()),
  );
watch(
  identity,
  () => {
    request?.abort();
    request = null;
    values.value = emptyWriteOffDraft();
    errors.value = { lineFields: {} };
    error.value = "";
    pending.value = false;
    activeKey.value = "";
    attempt.clear();
    create.reset();
  },
  { flush: "sync" },
);
function clearErrors(): void {
  errors.value = { lineFields: {} };
  error.value = "";
}
function changeLine(key: string, line: WriteOffDraftLine): void {
  if (disabled.value) return;
  values.value.lines = values.value.lines.map((l) =>
    l.key === key ? { ...line } : l,
  );
  clearErrors();
}
function addLine(): void {
  if (disabled.value || values.value.lines.length >= 100) return;
  values.value.lines.push(newWriteOffLine(crypto.randomUUID()));
  clearErrors();
}
function removeLine(key: string): void {
  if (disabled.value) return;
  values.value.lines = values.value.lines.filter((l) => l.key !== key);
  clearErrors();
}
function selectSku(key: string, option: InventorySkuOption): void {
  const old = values.value.lines.find((l) => l.key === key);
  if (!old) return;
  changeLine(key, {
    ...old,
    inventoryItemId: option.id,
    sku: option.sku,
    baseUom: option.baseUom,
    uom: option.baseUom,
  });
  sku.reset();
  activeKey.value = "";
}
function clearSku(key: string): void {
  const old = values.value.lines.find((l) => l.key === key);
  if (old)
    changeLine(key, {
      ...old,
      inventoryItemId: "",
      sku: "",
      baseUom: "",
      uom: "",
    });
}
function searchSku(key: string, value: string): void {
  if (disabled.value) return;
  activeKey.value = key;
  sku.search.value = value;
}
async function save(): Promise<void> {
  if (pending.value || !scope.ready.value) return;
  errors.value = validateWriteOffDraft(values.value);
  if (hasWriteOffErrors(errors.value)) return;
  if (
    values.value.lines.length &&
    (!uoms.data.value?.length || uoms.error.value)
  ) {
    error.value =
      "Не удалось проверить справочник единиц. Повторите его загрузку.";
    return;
  }
  const captured = identity.value,
    controller = new AbortController();
  request = controller;
  pending.value = true;
  error.value = "";
  try {
    const sent = attempt.begin(copyWriteOffDraft(values.value), () =>
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
      name: "inventory-write-off-document",
      params: { documentId: result.id },
    });
  } catch (cause: unknown) {
    if (controller.signal.aborted || captured !== identity.value) return;
    errors.value =
      cause instanceof WriteOffRequestError ? cause.fields : { lineFields: {} };
    error.value =
      cause instanceof Error ? cause.message : "Не удалось создать списание.";
    attempt.fail(
      !(cause instanceof WriteOffRequestError) ||
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
        window.confirm("Есть несохранённый черновик. Покинуть страницу?")))
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
    aria-label="Создание черновика списания"
  >
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Новое списание</h1>
      <Button
        variant="outline"
        :disabled="pending"
        @click="router.push({ name: 'inventory-write-off-documents' })"
        >К списку</Button
      >
    </header>
    <p class="text-sm text-muted-foreground">
      Сохраняется только план. Физические остатки ещё не изменяются.
    </p>
    <p v-if="scope.error.value" role="alert" class="text-destructive">
      {{ scope.error.value }}
    </p>
    <form
      class="flex w-full max-w-5xl shrink-0 flex-col gap-5 rounded-lg border bg-card p-4 sm:p-6"
      @submit.prevent="save"
    >
      <WriteOffReasonField
        :value="values.reason"
        :error="errors.reason"
        :disabled="disabled"
        @change="
          values.reason = $event;
          clearErrors();
        "
      />
      <div class="grid gap-5 lg:grid-cols-2">
        <div>
          <WriteOffReferencePicker
            label="Склад"
            :search="lookup.warehouses.search.value"
            :items="lookup.warehouses.items.value"
            :selected-id="values.warehouseId"
            :selected-name="values.warehouseName"
            :loading="lookup.warehouses.loading.value"
            :error="lookup.warehouses.error.value"
            :offset="lookup.warehouses.offset.value"
            :total="lookup.warehouses.total.value"
            :disabled="disabled"
            @search="lookup.warehouses.setSearch"
            @select="
              values.warehouseId = $event.id;
              values.warehouseName = $event.name;
              clearErrors();
            "
            @page="lookup.warehouses.page"
            @retry="lookup.warehouses.retry"
          />
          <p
            v-if="errors.warehouseId"
            role="alert"
            class="mt-1 text-sm text-destructive"
          >
            {{ errors.warehouseId }}
          </p>
        </div>
        <div>
          <WriteOffReferencePicker
            label="Компания-владелец"
            :search="lookup.owners.search.value"
            :items="lookup.owners.items.value"
            :selected-id="values.ownerId"
            :selected-name="values.ownerName"
            :loading="lookup.owners.loading.value"
            :error="lookup.owners.error.value"
            :offset="lookup.owners.offset.value"
            :total="lookup.owners.total.value"
            :disabled="disabled"
            @search="lookup.owners.setSearch"
            @select="
              values.ownerId = $event.id;
              values.ownerName = $event.name;
              clearErrors();
            "
            @page="lookup.owners.page"
            @retry="lookup.owners.retry"
          />
          <p class="mt-1 text-xs text-muted-foreground">
            Владелец товара выбирается явно и не обязательно является
            поставщиком.
          </p>
          <p
            v-if="errors.ownerId"
            role="alert"
            class="mt-1 text-sm text-destructive"
          >
            {{ errors.ownerId }}
          </p>
        </div>
      </div>
      <p v-if="uoms.error.value" role="alert" class="text-sm text-destructive">
        {{ uoms.error.value.message }}
        <Button
          type="button"
          variant="outline"
          :disabled="pending || uoms.isFetching.value"
          @click="uoms.refetch()"
          >Повторить загрузку единиц</Button
        >
      </p>
      <WriteOffDraftLinesForm
        :lines="values.lines"
        :errors="errors"
        :disabled="disabled"
        :active-key="activeKey"
        :search="sku.search.value"
        :options="sku.options.value"
        :loading="sku.loading.value"
        :error="sku.error.value"
        :total="sku.total.value"
        :uoms="uoms.data.value ?? []"
        @change="changeLine"
        @add="addLine"
        @remove="removeLine"
        @search="searchSku"
        @select="selectSku"
        @clear="clearSku"
        @retry="sku.retry"
      />
      <p
        v-if="error"
        role="alert"
        class="rounded-md border border-destructive p-3 text-sm text-destructive"
      >
        {{ error }}
      </p>
      <p
        v-if="attempt.uncertain"
        role="alert"
        class="rounded-md bg-muted p-3 text-sm"
      >
        Ответ сервера не получен однозначно. Повторите исходный запрос: он
        использует прежний ключ и не создаст второй документ. Введённые данные
        сохранены.
      </p>
      <Button
        class="self-start"
        type="submit"
        :disabled="pending || !scope.ready.value"
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
