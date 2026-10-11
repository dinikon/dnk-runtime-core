<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { itemFromDto } from "../../api/catalog.mapper";
import { useCatalogContext } from "../../model/use-catalog-context";
import {
  loadAttributes,
  loadCategories,
  loadTags,
} from "../../model/catalog-options";
import type {
  ItemSection,
  StructureDTO,
  ReadItemDTO,
} from "../../api/catalog.dto";
import CatalogToolbar from "../CatalogToolbar.vue";
import CatalogItemFieldsForm from "../forms/CatalogItemFieldsForm.vue";
import CatalogItemGalleryForm from "../forms/CatalogItemGalleryForm.vue";
import CatalogItemStructureForm from "../forms/CatalogItemStructureForm.vue";
import ProductCategoriesForm from "../forms/ProductCategoriesForm.vue";
import ProductTagsForm from "../forms/ProductTagsForm.vue";
const dirty = ref<Record<string, boolean>>({}),
  reset = ref<Record<string, number>>({}),
  pending = ref(false),
  error = ref(""),
  conflict = ref(false),
  cache = useQueryClient();
const ctx = useCatalogContext(
  () => Object.values(dirty.value).some(Boolean),
  () => pending.value,
  () => {
    dirty.value = {};
    error.value = "";
  },
);
const id = computed(() => String(ctx.route.params.itemId));
const item = useQuery({
  queryKey: computed(() => ctx.key("get-item", id.value)),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  refetchOnWindowFocus: false,
  queryFn: async ({ signal }) =>
    itemFromDto(
      (await catalogApi.getItem(id.value, ctx.locale.value, signal)).item,
    ),
});
const attributes = useQuery({
  queryKey: computed(() => ctx.key("attribute-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadAttributes(ctx.locale.value, signal),
});
const categories = useQuery({
  queryKey: computed(() => ctx.key("category-options")),
  enabled: computed(
    () => item.data.value?.kind === "simple" && !!ctx.locale.value,
  ),
  queryFn: ({ signal }) => loadCategories(ctx.locale.value, signal),
});
const tags = useQuery({
  queryKey: computed(() => ctx.key("tag-options")),
  enabled: computed(
    () => item.data.value?.kind === "simple" && !!ctx.locale.value,
  ),
  queryFn: ({ signal }) => loadTags(ctx.locale.value, signal),
});
const variants = useQuery({
  queryKey: computed(() => ctx.key("family-variants", id.value)),
  enabled: computed(() => item.data.value?.kind === "variable"),
  refetchOnWindowFocus: false,
  queryFn: async ({ signal }) => {
    const rows: ReadItemDTO[] = [];
    for (let offset = 0; ; offset += 100) {
      const page = await catalogApi.listVariants(
        id.value,
        ctx.locale.value,
        offset,
        100,
        signal,
      );
      rows.push(...page.items);
      if (rows.length >= page.total) return rows;
    }
  },
});
const structure = computed<StructureDTO | null>(() => {
  const value = item.data.value;
  if (!value || value.kind !== "variable" || !variants.data.value) return null;
  return {
    axes: value.own.axes,
    default_selection:
      value.own.default_selection?.values.map(([attribute_id, option_id]) => ({
        attribute_id,
        option_id,
      })) ?? null,
    variants: variants.data.value.map((v) => ({
      item_id: v.own.id,
      selection: v.own.selection.values.map(([attribute_id, option_id]) => ({
        attribute_id,
        option_id,
      })),
    })),
  };
});
const revision = ref(0);
watch(
  () => item.data.value,
  (value) => {
    if (value && !Object.values(dirty.value).some(Boolean))
      revision.value = value.rootRevision;
  },
);
watch(
  () => [id.value, ctx.locale.value],
  () => {
    dirty.value = {};
    reset.value = {};
    error.value = "";
    conflict.value = false;
    revision.value = item.data.value?.rootRevision ?? 0;
  },
);
const sections = computed<ItemSection[]>(() => [
  "content",
  "status",
  ...(item.data.value?.kind === "variable" ? [] : ["sku" as const]),
  "virtual",
  "price",
  "stock",
  "measurements",
  "metadata",
  "attributes",
]);
const titles: Partial<Record<ItemSection, string>> = {
  content: "Контент",
  status: "Статус",
  sku: "SKU",
  virtual: "Виртуальный товар",
  price: "Цена",
  stock: "Наличие",
  measurements: "Вес и размеры",
  metadata: "Дополнительные поля",
  attributes: "Характеристики",
};
async function mutate(section: ItemSection, action: () => Promise<unknown>) {
  pending.value = true;
  error.value = "";
  conflict.value = false;
  const current = ctx.captureSession();
  try {
    await action();
    if (!current()) return;
    dirty.value[section] = false;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
      refetchType: "none",
    });
    const fresh = await item.refetch();
    revision.value = fresh.data?.rootRevision ?? revision.value;
    reset.value[section] = (reset.value[section] ?? 0) + 1;
    if (section === "structure" || section === "kind") await variants.refetch();
  } catch (e) {
    if (current()) {
      error.value = getApiErrorMessage(e, "Не удалось выполнить операцию");
      conflict.value = getApiErrorStatus(e) === 409;
    }
  } finally {
    if (current()) pending.value = false;
  }
}
function save(section: ItemSection, value: Record<string, unknown>) {
  return mutate(section, () =>
    catalogApi.saveItem(
      id.value,
      section,
      revision.value,
      value,
      ctx.locale.value,
    ),
  );
}
function inherit(section: "content" | "galleries") {
  return mutate(section, () =>
    catalogApi.inheritSection(
      id.value,
      section,
      ctx.locale.value,
      revision.value,
    ),
  );
}
function replaceStructure(value: StructureDTO) {
  const ids = new Set(value.variants.map((v) => v.item_id));
  const removed =
    variants.data.value
      ?.filter((v) => !ids.has(v.own.id))
      .map((v) => v.own.id) ?? [];
  if (
    removed.length &&
    !window.confirm(`Будут удалены ${removed.length} вариантов. Продолжить?`)
  )
    return;
  void save("structure", { structure: value, removed_ids: removed });
}
async function reload() {
  if (
    Object.values(dirty.value).some(Boolean) &&
    !window.confirm("Отказаться от ввода и загрузить актуальную карточку?")
  )
    return;
  dirty.value = {};
  error.value = "";
  conflict.value = false;
  const fresh = await item.refetch();
  revision.value = fresh.data?.rootRevision ?? 0;
  for (const section of [
    ...sections.value,
    "galleries",
    "categories",
    "tags",
    "structure",
  ])
    reset.value[section] = (reset.value[section] ?? 0) + 1;
}
const transition = ref(false),
  selectedChild = ref(""),
  carry = ref(0);
function toVariable(value: StructureDTO) {
  void save("kind", {
    kind: "variable",
    structure: value,
    carry_to_index: item.data.value?.own.sku ? carry.value : null,
  });
  transition.value = false;
}
function toSimple() {
  if (
    !selectedChild.value ||
    !window.confirm(
      "Выбранный вариант станет простым товаром. Все ID вариантов будут удалены. Продолжить?",
    )
  )
    return;
  void save("kind", {
    kind: "simple",
    selected_item_id: selectedChild.value,
    discarded_ids: variants.data.value?.map((v) => v.own.id) ?? [],
  });
}
</script>
<template>
  <div class="mx-auto min-w-0 max-w-5xl space-y-5 p-6">
    <div class="flex flex-wrap justify-between gap-3">
      <div class="min-w-0">
        <h1 class="break-words text-2xl font-semibold">
          {{ item.data.value?.title ?? "Карточка товара" }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ item.data.value?.kind }} · Ревизия семьи {{ revision }} · Default
        </p>
      </div>
      <Button variant="outline" :disabled="pending" @click="reload"
        >Загрузить актуальные данные</Button
      >
    </div>
    <CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <p
      v-if="error || item.isError.value"
      role="alert"
      class="rounded border p-4"
    >
      {{
        error ||
        getApiErrorMessage(item.error.value, "Не удалось выполнить операцию")
      }}<span v-if="conflict" class="block mt-2"
        >Ввод сохранён. Загрузите актуальную версию явно, затем повторите
        изменение.</span
      >
    </p>
    <p v-if="item.isPending.value">Загрузка…</p>
    <template v-if="item.data.value"
      ><Button
        v-if="item.data.value.kind === 'variant'"
        variant="outline"
        @click="
          ctx.router.push({
            path: `/catalog/items/${item.data.value.rootId}`,
            query: { locale: ctx.locale.value },
          })
        "
        >Открыть родителя</Button
      >
      <section
        v-for="section in sections"
        :key="`${id}:${ctx.locale.value}:${section}`"
        class="space-y-4 rounded-lg border p-5"
      >
        <h2 class="text-lg font-medium">{{ titles[section] }}</h2>
        <CatalogItemFieldsForm
          :item="item.data.value"
          :section="section"
          :locale="ctx.locale.value"
          :pending="pending || !ctx.active.value || conflict"
          :reset="reset[section] ?? 0"
          :attributes="attributes.data.value ?? []"
          @dirty="(value) => (dirty[section] = value)"
          @save="(value) => save(section, value)"
          @inherit="inherit('content')"
        />
      </section>
      <section class="space-y-4 rounded-lg border p-5">
        <h2 class="text-lg font-medium">
          Изображения · {{ ctx.locale.value }}
        </h2>
        <CatalogItemGalleryForm
          :key="`${id}:${ctx.locale.value}`"
          :own="item.data.value.own.galleries[ctx.locale.value] ?? null"
          :effective="item.data.value.effective.gallery"
          :variant="item.data.value.kind === 'variant'"
          :pending="pending || !ctx.active.value || conflict"
          :reset="reset.galleries ?? 0"
          :image-url="
            (imageId) => catalogApi.imageUrl(id, ctx.locale.value, imageId)
          "
          @dirty="(value) => (dirty.galleries = value)"
          @save="(gallery) => save('galleries', { gallery })"
          @inherit="inherit('galleries')"
          @upload="
            (file, main) =>
              mutate('galleries', () =>
                catalogApi.uploadImage(
                  id,
                  ctx.locale.value,
                  revision,
                  file,
                  main,
                ),
              )
          "
        />
      </section>
      <template v-if="item.data.value.kind === 'simple'"
        ><section class="rounded-lg border p-5 space-y-4">
          <h2 class="text-lg font-medium">Категории</h2>
          <ProductCategoriesForm
            :ids="item.data.value.own.category_ids"
            :primary-id="item.data.value.own.primary_category_id"
            :categories="categories.data.value ?? []"
            :pending="pending"
            :disabled="!ctx.active.value || conflict"
            :reset="reset.categories ?? 0"
            @dirty="(value) => (dirty.categories = value)"
            @submit="
              (category_ids, primary_category_id) =>
                save('categories', { category_ids, primary_category_id })
            "
          />
        </section>
        <section class="rounded-lg border p-5 space-y-4">
          <h2 class="text-lg font-medium">Метки</h2>
          <ProductTagsForm
            :ids="item.data.value.own.tag_ids"
            :tags="tags.data.value ?? []"
            :pending="pending"
            :disabled="!ctx.active.value || conflict"
            :reset="reset.tags ?? 0"
            @dirty="(value) => (dirty.tags = value)"
            @submit="(tag_ids) => save('tags', { tag_ids })"
          /></section
      ></template>
      <section
        v-if="item.data.value.kind === 'variable'"
        class="space-y-4 rounded-lg border p-5"
      >
        <h2 class="text-lg font-medium">Варианты</h2>
        <p v-if="variants.isError.value" role="alert">
          {{
            getApiErrorMessage(
              variants.error.value,
              "Не удалось выполнить операцию",
            )
          }}
        </p>
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="v in variants.data.value ?? []"
            :key="v.own.id"
            variant="outline"
            @click="
              ctx.router.push({
                path: `/catalog/items/${id}/variants/${v.own.id}`,
                query: { locale: ctx.locale.value },
              })
            "
            >{{
              v.effective.content?.name ??
              v.own.selection.values
                .map(
                  ([a, o]) =>
                    attributes.data.value
                      ?.find((x) => x.id === a)
                      ?.options.find((x) => x.id === o)?.label ?? o,
                )
                .join(" / ")
            }}</Button
          >
        </div>
        <CatalogItemStructureForm
          v-if="structure"
          :initial="structure"
          :attributes="attributes.data.value ?? []"
          :pending="pending || conflict"
          :reset="reset.structure ?? 0"
          @dirty="(value) => (dirty.structure = value)"
          @submit="replaceStructure"
        /><label class="block"
          >Преобразовать в простой товар<select
            v-model="selectedChild"
            class="w-full rounded border bg-background p-2"
          >
            <option value="">Выберите сохраняемый вариант</option>
            <option
              v-for="v in variants.data.value ?? []"
              :key="v.own.id"
              :value="v.own.id"
            >
              {{ v.effective.content?.name ?? v.own.id }}
            </option>
          </select></label
        ><Button
          variant="outline"
          :disabled="pending || conflict || !selectedChild"
          @click="toSimple"
          >Преобразовать в простой</Button
        >
      </section>
      <section
        v-if="item.data.value.kind === 'simple'"
        class="space-y-4 rounded-lg border p-5"
      >
        <Button
          variant="outline"
          :disabled="
            pending ||
            conflict ||
            !!item.data.value.own.category_ids.length ||
            !!item.data.value.own.tag_ids.length
          "
          @click="transition = !transition"
          >Преобразовать в товар с вариантами</Button
        >
        <p class="text-sm text-muted-foreground">
          Перед преобразованием снимите категории и метки.
        </p>
        <template v-if="transition"
          ><label v-if="item.data.value.own.sku" class="block"
            >Номер варианта для переноса SKU (с нуля)<input
              v-model.number="carry"
              type="number"
              min="0"
              class="w-full rounded border bg-background p-2" /></label
          ><CatalogItemStructureForm
            :initial="null"
            :attributes="attributes.data.value ?? []"
            :pending="pending || conflict"
            :reset="reset.kind ?? 0"
            @dirty="(value) => (dirty.kind = value)"
            @submit="toVariable"
        /></template></section
    ></template>
  </div>
</template>
