<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { catalogApi } from "../../api/catalog.api";
import { getApiErrorMessage } from "@/app/providers/http";
import { useCatalogContext } from "../../model/use-catalog-context";
import { loadAttributes } from "../../model/catalog-options";
import type { StructureDTO } from "../../api/catalog.dto";
import CatalogItemStructureForm from "../forms/CatalogItemStructureForm.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
const kind = ref("simple"),
  virtual = ref(false),
  dirty = ref(false),
  pending = ref(false),
  error = ref(""),
  cache = useQueryClient();
const ctx = useCatalogContext(
  () => dirty.value,
  () => pending.value,
);
const attributes = useQuery({
  queryKey: computed(() => ctx.key("attribute-options")),
  enabled: computed(
    () =>
      !!ctx.locale.value && !!ctx.tenantId.value && kind.value === "variable",
  ),
  queryFn: ({ signal }) => loadAttributes(ctx.locale.value, signal),
});
async function create(structure?: StructureDTO) {
  pending.value = true;
  error.value = "";
  const current = ctx.captureSession();
  try {
    const result = structure
      ? await catalogApi.createVariable(structure)
      : await catalogApi.createSimple(virtual.value);
    if (!current()) return;
    dirty.value = false;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
    });
    pending.value = false;
    await ctx.router.push({
      path: `/catalog/items/${result.id}`,
      query: { locale: ctx.locale.value },
    });
  } catch (e) {
    if (current())
      error.value = getApiErrorMessage(e, "Не удалось выполнить операцию");
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div
    class="mx-auto min-h-0 w-full min-w-0 max-w-4xl flex-1 space-y-5 overflow-y-auto p-6"
  >
    <h1 class="text-2xl font-semibold">Новый товар</h1>
    <CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <p class="text-sm text-muted-foreground">
      Тип контента: Default · Название, описание, краткое описание
    </p>
    <label class="block"
      ><span class="block mb-1">Вид товара</span
      ><select
        v-model="kind"
        :disabled="pending"
        class="w-full rounded border bg-background p-2"
        @change="dirty = true"
      >
        <option value="simple">Простой товар</option>
        <option value="variable">Товар с вариантами</option>
      </select></label
    >
    <p v-if="error || attributes.isError.value" role="alert">
      {{
        error ||
        getApiErrorMessage(
          attributes.error.value,
          "Не удалось выполнить операцию",
        )
      }}
    </p>
    <form v-if="kind === 'simple'" class="space-y-4" @submit.prevent="create()">
      <label class="flex gap-2"
        ><input
          v-model="virtual"
          type="checkbox"
          :disabled="pending"
          @change="dirty = true"
        />Виртуальный товар</label
      ><Button :disabled="pending || !ctx.active.value" type="submit"
        >Создать товар</Button
      >
    </form>
    <CatalogItemStructureForm
      v-else
      :initial="null"
      :attributes="attributes.data.value ?? []"
      :pending="pending || !ctx.active.value || attributes.isPending.value"
      :reset="0"
      @dirty="(value) => (dirty = value)"
      @submit="create"
    />
  </div>
</template>
