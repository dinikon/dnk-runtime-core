<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { loadTypes, loadAttributes } from "../../model/catalog-options";
import { useCatalogContext } from "../../model/use-catalog-context";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import { structureToDto } from "../../api/catalog.mapper";
import type { ProductStructureDraft } from "../../model/catalog.types";
import ProductCreateForm from "../forms/ProductCreateForm.vue";
const dirty = ref(false),
  pending = ref(false),
  error = ref("");
const ctx = useCatalogContext(
  () => dirty.value,
  () => pending.value,
  () => {
    dirty.value = false;
    error.value = "";
    pending.value = false;
  },
);
const types = useQuery({
  queryKey: computed(() => ctx.key("type-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadTypes(ctx.locale.value, signal),
});
const attributes = useQuery({
  queryKey: computed(() => ctx.key("attribute-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadAttributes(ctx.locale.value, signal),
});
watch(
  () => ctx.locale.value,
  () => {
    dirty.value = false;
    error.value = "";
  },
);
async function create(typeId: string, structure: ProductStructureDraft) {
  const current = ctx.captureSession();
  if (pending.value) return;
  pending.value = true;
  error.value = "";
  try {
    const dto = structureToDto(structure);
    const product =
      dto.kind === "simple"
        ? await catalogApi.createSimpleProduct({
            product_type_id: typeId || null,
            virtual: dto.variant.virtual,
          })
        : await catalogApi.createVariableProduct({
            product_type_id: typeId || null,
            structure: dto,
          });
    if (!current()) return;
    dirty.value = false;
    pending.value = false;
    await ctx.router.push({
      path: `/catalog/products/${product.id}`,
      query: { locale: ctx.locale.value },
    });
    if (!current()) return;
  } catch (e) {
    if (!current()) return;
    error.value = getApiErrorMessage(
      e,
      "Создание не подтверждено. Проверьте список перед повтором.",
    );
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div class="max-w-3xl space-y-6 p-6">
    <CatalogHeader
      title="Новый товар"
      description="Выберите SIMPLE или VARIABLE, тип контента и продаваемые позиции."
    /><CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <p
      v-if="error || types.isError.value || attributes.isError.value"
      role="alert"
      class="text-destructive"
    >
      {{ error || "Не удалось загрузить типы контента или характеристики." }}
    </p>
    <ProductCreateForm
      v-if="ctx.locale.value && types.data.value"
      :key="ctx.locale.value + ctx.sessionKey.value"
      :types="types.data.value"
      :attributes="attributes.data.value ?? []"
      :pending="pending"
      :disabled="
        types.isError.value ||
        attributes.isError.value ||
        attributes.isPending.value
      "
      @dirty="dirty = $event"
      @submit="create"
    />
  </div>
</template>
