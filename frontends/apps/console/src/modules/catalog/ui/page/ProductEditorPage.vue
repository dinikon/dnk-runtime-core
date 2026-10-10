<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import {
  productFromDto,
  typeFromDto,
  variantFromDto,
  structureToDto,
} from "../../api/catalog.mapper";
import {
  loadTypes,
  loadAttributes,
  loadCategories,
  loadTags,
} from "../../model/catalog-options";
import { useCatalogContext } from "../../model/use-catalog-context";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import type {
  ProductStructureDraft,
  ProductAttributeValue,
} from "../../model/catalog.types";
import ProductAttributesForm from "../forms/ProductAttributesForm.vue";
import ProductCategoriesForm from "../forms/ProductCategoriesForm.vue";
import ProductTagsForm from "../forms/ProductTagsForm.vue";
import ProductStructureForm from "../forms/ProductStructureForm.vue";
import ProductVariantsPanel from "../ProductVariantsPanel.vue";
import ContentForm from "../forms/ContentForm.vue";
import VariantPropertiesForm from "../forms/VariantPropertiesForm.vue";
import ProductTypeSelectionForm from "../forms/ProductTypeSelectionForm.vue";
const dirty = ref<Record<string, boolean>>({}),
  pending = ref(false),
  error = ref(""),
  conflict = ref(false),
  resets = ref({
    PRODUCT: 0,
    VARIANT: 0,
    properties: 0,
    type: 0,
    structure: 0,
    kind: 0,
    attributes: 0,
    categories: 0,
    tags: 0,
  });
const cache = useQueryClient();
const ctx = useCatalogContext(
  () => Object.values(dirty.value).some(Boolean),
  () => pending.value,
  () => {
    dirty.value = {};
    error.value = "";
    pending.value = false;
    conflict.value = false;
  },
);
const id = computed(() => String(ctx.route.params.productId));
const product = useQuery({
  queryKey: computed(() => ctx.key("get-product", id.value)),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  refetchOnWindowFocus: false,
  queryFn: ({ signal }) =>
    catalogApi.getProduct(id.value, ctx.locale.value, signal),
  select: productFromDto,
});
const variant = useQuery({
  queryKey: computed(() =>
    ctx.key("get-variant", id.value, ctx.route.params.variantId),
  ),
  enabled: computed(
    () =>
      !!ctx.route.params.variantId &&
      !!ctx.locale.value &&
      !!ctx.tenantId.value,
  ),
  refetchOnWindowFocus: false,
  queryFn: ({ signal }) =>
    catalogApi.getVariant(
      id.value,
      String(ctx.route.params.variantId),
      ctx.locale.value,
      signal,
    ),
  select: variantFromDto,
});
const types = useQuery({
  queryKey: computed(() => ctx.key("type-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadTypes(ctx.locale.value, signal),
});
const schema = useQuery({
  queryKey: computed(() =>
    ctx.key("get-product-type", product.data.value?.typeId),
  ),
  enabled: computed(
    () => !!product.data.value && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  queryFn: ({ signal }) =>
    catalogApi.getProductType(
      product.data.value!.typeId,
      ctx.locale.value,
      signal,
    ),
  select: typeFromDto,
});
const attributes = useQuery({
  queryKey: computed(() => ctx.key("attribute-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadAttributes(ctx.locale.value, signal),
});
const categories = useQuery({
  queryKey: computed(() => ctx.key("category-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadCategories(ctx.locale.value, signal),
});
const tags = useQuery({
  queryKey: computed(() => ctx.key("tag-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadTags(ctx.locale.value, signal),
});
const selectedVariant = computed(() =>
  ctx.route.params.variantId
    ? product.data.value?.variants.find(
        (v) => v.id === String(ctx.route.params.variantId),
      )
    : product.data.value?.kind === "simple"
      ? product.data.value.variants[0]
      : undefined,
);
const tabs = computed(() => [
  { id: "PRODUCT", label: "Контент товара" },
  ...(product.data.value?.kind === "variable" && selectedVariant.value
    ? [{ id: "VARIANT", label: "Контент варианта" }]
    : []),
  ...(selectedVariant.value
    ? [{ id: "properties", label: "Свойства позиции" }]
    : []),
  ...(product.data.value?.kind === "variable"
    ? [{ id: "structure", label: "Позиции и оси" }]
    : []),
  { id: "attributes", label: "Характеристики" },
  { id: "categories", label: "Категории" },
  { id: "tags", label: "Метки" },
  { id: "type", label: "Тип контента" },
  { id: "kind", label: "Смена вида" },
]);
const section = computed(() => {
  const requested = String(
    ctx.route.query.section ??
      (ctx.route.params.variantId
        ? product.data.value?.kind === "variable"
          ? "VARIANT"
          : "properties"
        : "PRODUCT"),
  );
  return tabs.value.some((t) => t.id === requested) ? requested : "PRODUCT";
});
const titleInheritance = computed(
  () =>
    schema.data.value?.blocks.some(
      (b) => b.code === "title" && b.scope === "PRODUCT",
    ) &&
    schema.data.value?.blocks.some(
      (b) => b.code === "title" && b.scope === "VARIANT",
    ),
);
const failure = computed(() =>
  variant.isError.value
    ? "Позиция не найдена или недоступна."
    : product.isError.value
      ? getApiErrorStatus(product.error.value) === 404
        ? "Товар не найден."
        : getApiErrorStatus(product.error.value) === 403
          ? "Нет доступа к товару."
          : "Не удалось загрузить товар."
      : schema.isError.value
        ? "Не удалось загрузить схему."
        : "",
);
watch(
  () => [ctx.locale.value, id.value, ctx.route.params.variantId],
  () => {
    dirty.value = {};
    error.value = "";
    conflict.value = false;
  },
);
watch(section, (_next, previous) => {
  dirty.value[previous] = false;
});
async function act(
  section: keyof typeof resets.value,
  fn: () => Promise<unknown>,
) {
  const current = ctx.captureSession();
  if (pending.value || conflict.value) return;
  pending.value = true;
  error.value = "";
  try {
    await fn();
    if (!current()) return;
    const read = await product.refetch();
    if (read.isError) throw read.error;
    if (
      ctx.route.params.variantId &&
      product.data.value?.variants.some(
        (v) => v.id === String(ctx.route.params.variantId),
      )
    )
      await variant.refetch();
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
      refetchType: "none",
    });
    if (!current()) return;
    await schema.refetch();
    if (!current()) return;
    resets.value[section]++;
    dirty.value[section] = false;
    return true;
  } catch (e) {
    if (!current()) return;
    conflict.value =
      getApiErrorStatus(e) === 409 ||
      getApiErrorStatus(e) === null ||
      (getApiErrorStatus(e) ?? 0) >= 500;
    error.value = getApiErrorMessage(
      e,
      "Сохранение не подтверждено. Загрузите состояние перед повторной записью.",
    );
  } finally {
    if (current()) pending.value = false;
  }
}
function content(values: Record<string, string>) {
  const p = product.data.value,
    s = schema.data.value;
  if (!p || !s) return;
  const body = {
    expected_revision: p.revision,
    expected_schema_version: s.schemaVersion,
    values,
  };
  if (section.value === "VARIANT" && selectedVariant.value)
    void act("VARIANT", () =>
      catalogApi.putVariantContent(
        p.id,
        selectedVariant.value!.id,
        ctx.locale.value,
        body,
      ),
    );
  else
    void act("PRODUCT", () =>
      catalogApi.putProductContent(p.id, ctx.locale.value, body),
    );
}
function removeContent() {
  const p = product.data.value;
  if (!p || !window.confirm("Удалить перевод выбранной locale?")) return;
  if (section.value === "VARIANT" && selectedVariant.value)
    void act("VARIANT", () =>
      catalogApi.deleteVariantContent(
        p.id,
        selectedVariant.value!.id,
        ctx.locale.value,
        p.revision,
      ),
    );
  else
    void act("PRODUCT", () =>
      catalogApi.deleteProductContent(p.id, ctx.locale.value, p.revision),
    );
}
function properties(virtual: boolean) {
  const p = product.data.value;
  if (p && selectedVariant.value)
    void act("properties", () =>
      catalogApi.setVariantProperties(p.id, selectedVariant.value!.id, {
        expected_revision: p.revision,
        virtual,
        downloadable: false,
      }),
    );
}
function changeType(typeId: string) {
  const p = product.data.value;
  if (p)
    void act("type", () =>
      catalogApi.changeProductType(p.id, {
        expected_revision: p.revision,
        product_type_id: typeId,
      }),
    );
}
async function saveStructure(value: ProductStructureDraft) {
  const p = product.data.value;
  if (!p) return;
  const dto = structureToDto(value);
  if (section.value === "kind") {
    if (dto.kind === p.kind) {
      error.value = "Выберите другой вид товара.";
      return;
    }
    if (
      !window.confirm(
        `Сменить ${p.kind.toUpperCase()} на ${dto.kind.toUpperCase()}? Контент товара сохраняется. Изменения позиций показаны в редакторе; переводы не удаляются автоматически.`,
      )
    )
      return;
    const success = await act("kind", () =>
      catalogApi.changeProductKind(p.id, {
        expected_revision: p.revision,
        structure: dto,
      }),
    );
    if (success) {
      dirty.value = {};
      pending.value = false;
      await ctx.router.push({
        path: `/catalog/products/${p.id}`,
        query: { locale: ctx.locale.value },
      });
    }
  } else if (dto.kind === "variable") {
    const removed = p.variants.filter(
      (v) => !dto.variants.some((row) => row.variant_id === v.id),
    );
    if (
      removed.length &&
      !window.confirm(
        `Удалить ${removed.length} позиций? Сервер проверит отсутствие переводов.`,
      )
    )
      return;
    await act("structure", () =>
      catalogApi.replaceVariants(p.id, {
        expected_revision: p.revision,
        structure: dto,
      }),
    );
  }
}
function saveAttributes(values: ProductAttributeValue[]) {
  const p = product.data.value;
  if (p)
    void act("attributes", () =>
      catalogApi.setProductAttributes(p.id, {
        expected_revision: p.revision,
        values: values.map((v) => ({
          attribute_id: v.attributeId,
          option_id: v.optionId,
          visible: v.visible,
          position: v.position,
        })),
      }),
    );
}
function saveCategories(ids: string[], primary: string | null) {
  const p = product.data.value;
  if (p)
    void act("categories", () =>
      catalogApi.setProductCategories(p.id, {
        expected_revision: p.revision,
        category_ids: ids,
        primary_category_id: primary,
      }),
    );
}
function saveTags(ids: string[]) {
  const p = product.data.value;
  if (p)
    void act("tags", () =>
      catalogApi.setProductTags(p.id, {
        expected_revision: p.revision,
        tag_ids: ids,
      }),
    );
}
function openVariant(variantId: string) {
  void ctx.router.push({
    path: `/catalog/products/${id.value}/variants/${variantId}`,
    query: { locale: ctx.locale.value },
  });
}
async function reload() {
  const current = ctx.captureSession();
  if (
    Object.values(dirty.value).some(Boolean) &&
    !window.confirm(
      "Загрузить актуальное состояние и отменить локальные изменения?",
    )
  )
    return;
  const result = await product.refetch();
  if (!current()) return;
  if (result.isError) return;
  await schema.refetch();
  if (ctx.route.params.variantId) await variant.refetch();
  if (!current()) return;
  dirty.value = {};
  conflict.value = false;
  error.value = "";
  for (const key of Object.keys(resets.value) as (keyof typeof resets.value)[])
    resets.value[key]++;
}
async function remove() {
  const current = ctx.captureSession();
  const p = product.data.value;
  if (
    !p ||
    pending.value ||
    !window.confirm("Удалить товар и все его позиции?")
  )
    return;
  pending.value = true;
  try {
    await catalogApi.deleteProduct(p.id, p.revision);
    if (!current()) return;
    dirty.value = {};
    pending.value = false;
    await ctx.router.push({
      path: "/catalog/products",
      query: { locale: ctx.locale.value },
    });
    if (!current()) return;
  } catch (e) {
    if (!current()) return;
    error.value = getApiErrorMessage(e, "Удаление не подтверждено.");
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div class="max-w-4xl space-y-6 p-6">
    <CatalogHeader
      :title="
        product.data.value
          ? `${product.data.value.kind.toUpperCase()} · ${selectedVariant?.effectiveTitle ?? product.data.value.title ?? 'Товар'}`
          : 'Товар'
      "
      :description="
        product.data.value
          ? `ID ${product.data.value.id} · Ревизия ${product.data.value.revision}`
          : 'Карточка товара'
      "
    /><CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <div
      v-if="error || failure"
      role="alert"
      class="rounded-lg border border-destructive p-4"
    >
      <p>{{ error || failure }}</p>
      <p v-if="conflict" class="mt-2 text-sm">
        Ввод сохранён. Для продолжения явно загрузите актуальное состояние.
      </p>
      <Button class="mt-3" variant="outline" :disabled="pending" @click="reload"
        >Загрузить актуальное состояние</Button
      >
    </div>
    <p v-if="ctx.locale.value && product.isPending.value">Загрузка…</p>
    <template v-if="product.data.value && schema.data.value && !failure"
      ><nav class="flex flex-wrap gap-2">
        <Button
          v-for="tab in tabs"
          :key="tab.id"
          :variant="section === tab.id ? 'default' : 'outline'"
          @click="
            ctx.router.replace({
              query: { ...ctx.route.query, section: tab.id },
            })
          "
          >{{ tab.label }}</Button
        >
      </nav>
      <ContentForm
        v-if="section === 'PRODUCT' || section === 'VARIANT'"
        :key="
          id +
          String(ctx.route.params.variantId ?? '') +
          section +
          ctx.locale.value +
          ctx.sessionKey.value
        "
        :blocks="
          schema.data.value.blocks.filter(
            (b) => b.scope === (section === 'VARIANT' ? 'VARIANT' : 'PRODUCT'),
          )
        "
        :content="
          section === 'VARIANT'
            ? (selectedVariant?.content ?? null)
            : product.data.value.content
        "
        :title-inheritance="section === 'VARIANT' && !!titleInheritance"
        :inherited-title="product.data.value.title"
        :pending="pending"
        :disabled="!ctx.active.value || conflict"
        :reset="section === 'VARIANT' ? resets.VARIANT : resets.PRODUCT"
        @dirty="dirty[section] = $event"
        @submit="content"
        @delete="removeContent"
      /><VariantPropertiesForm
        v-if="section === 'properties' && selectedVariant"
        :key="selectedVariant.id + ctx.sessionKey.value"
        :virtual="selectedVariant.virtual"
        :pending="pending || conflict"
        :reset="resets.properties"
        @dirty="dirty.properties = $event"
        @submit="properties"
      /><ProductTypeSelectionForm
        v-if="section === 'type'"
        :key="id + ctx.sessionKey.value"
        :type-id="product.data.value.typeId"
        :types="types.data.value ?? []"
        :pending="pending || conflict"
        :reset="resets.type"
        @dirty="dirty.type = $event"
        @submit="changeType"
      />
      <template v-if="section === 'attributes'">
        <p v-if="attributes.isError.value" role="alert">
          Не удалось загрузить характеристики.
          <Button variant="outline" @click="attributes.refetch()"
            >Повторить</Button
          >
        </p>
        <p v-else-if="attributes.isPending.value">Загрузка…</p>
        <ProductAttributesForm
          v-else-if="attributes.data.value"
          :key="id + ctx.sessionKey.value"
          :values="product.data.value.attributeValues"
          :attributes="attributes.data.value"
          :pending="pending"
          :disabled="conflict"
          :reset="resets.attributes"
          @dirty="dirty.attributes = $event"
          @submit="saveAttributes"
        />
      </template>
      <template v-if="section === 'categories'">
        <p v-if="categories.isError.value" role="alert">
          Не удалось загрузить категории.
          <Button variant="outline" @click="categories.refetch()"
            >Повторить</Button
          >
        </p>
        <p v-else-if="categories.isPending.value">Загрузка…</p>
        <ProductCategoriesForm
          v-else-if="categories.data.value"
          :key="id + ctx.sessionKey.value"
          :ids="product.data.value.categoryIds"
          :primary-id="product.data.value.primaryCategoryId"
          :categories="categories.data.value"
          :pending="pending"
          :disabled="conflict"
          :reset="resets.categories"
          @dirty="dirty.categories = $event"
          @submit="saveCategories"
        />
      </template>
      <template v-if="section === 'tags'">
        <p v-if="tags.isError.value" role="alert">
          Не удалось загрузить метки.
          <Button variant="outline" @click="tags.refetch()">Повторить</Button>
        </p>
        <p v-else-if="tags.isPending.value">Загрузка…</p>
        <ProductTagsForm
          v-else-if="tags.data.value"
          :key="id + ctx.sessionKey.value"
          :ids="product.data.value.tagIds"
          :tags="tags.data.value"
          :pending="pending"
          :disabled="conflict"
          :reset="resets.tags"
          @dirty="dirty.tags = $event"
          @submit="saveTags"
        />
      </template>
      <template v-if="section === 'structure'"
        ><ProductVariantsPanel
          :variants="product.data.value.variants"
          :attributes="attributes.data.value ?? []"
          :pending="pending"
          @open="openVariant"
        />
        <p v-if="attributes.isError.value" role="alert">
          Не удалось загрузить характеристики.
        </p>
        <ProductStructureForm
          v-if="attributes.data.value"
          :key="id + ctx.sessionKey.value"
          :initial="product.data.value"
          :attributes="attributes.data.value"
          target-kind="variable"
          :pending="pending"
          :disabled="conflict"
          :reset="resets.structure"
          @dirty="dirty.structure = $event"
          @submit="saveStructure"
        />
      </template>
      <ProductStructureForm
        v-if="section === 'kind' && attributes.data.value"
        :key="id + ctx.sessionKey.value + 'kind'"
        :initial="product.data.value"
        :attributes="attributes.data.value"
        :target-kind="
          product.data.value.kind === 'simple' ? 'variable' : 'simple'
        "
        transition
        :pending="pending"
        :disabled="conflict"
        :reset="resets.kind"
        @dirty="dirty.kind = $event"
        @submit="saveStructure"
      />
      <p v-if="section === 'kind' && attributes.isError.value" role="alert">
        Не удалось загрузить характеристики. Повторите загрузку.
      </p>
      <p v-if="!ctx.active.value" class="text-sm text-muted-foreground">
        Locale неактивна: существующий перевод доступен для чтения, запись
        отключена.
      </p>
      <div class="border-t pt-4">
        <Button variant="ghost" :disabled="pending" @click="remove"
          >Удалить товар</Button
        >
      </div></template
    >
  </div>
</template>
