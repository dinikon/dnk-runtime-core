<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import {
  productItem,
  typeItem,
  blockItem,
  attributeItem,
  tagItem,
} from "../../api/catalog.mapper";
import { useCatalogContext } from "../../model/use-catalog-context";
import { loadTypes } from "../../model/catalog-options";
import type { CollectionKind, CollectionItem } from "../../model/catalog.types";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import CatalogSearchBar from "../CatalogSearchBar.vue";
import CatalogCollectionBody from "../CatalogCollectionBody.vue";
import CatalogResults from "../CatalogResults.vue";
import CatalogFooter from "../CatalogFooter.vue";
const props = defineProps<{ kind: CollectionKind }>();
const pending = ref(false),
  error = ref("");
const ctx = useCatalogContext(
  () => false,
  () => pending.value,
  () => {
    error.value = "";
    pending.value = false;
  },
);
const titles = {
  products: "Товары",
  attributes: "Характеристики",
  tags: "Метки",
  "product-types": "Типы контента",
  "content-blocks": "Блоки контента",
};
const search = computed(() => String(ctx.route.query.search ?? "")),
  page = computed(() => Math.max(1, Number(ctx.route.query.page) || 1)),
  typeId = computed(() => String(ctx.route.query.type ?? "")),
  productKind = computed(() =>
    ctx.route.query.kind === "simple" || ctx.route.query.kind === "variable"
      ? ctx.route.query.kind
      : undefined,
  );
const collection = useQuery({
  queryKey: computed(() =>
    ctx.key(
      "list",
      props.kind,
      search.value,
      page.value,
      typeId.value,
      productKind.value,
    ),
  ),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  refetchOnWindowFocus: false,
  queryFn: async ({ signal }) => {
    if (props.kind === "products") {
      const d = await catalogApi.listProducts(
        ctx.locale.value,
        search.value,
        page.value,
        20,
        typeId.value || undefined,
        signal,
        productKind.value,
      );
      return { ...d, items: d.items.map(productItem) };
    }
    if (props.kind === "tags") {
      const d = await catalogApi.listTags(
        ctx.locale.value,
        search.value,
        page.value,
        20,
        signal,
      );
      return { ...d, items: d.items.map(tagItem) };
    }
    if (props.kind === "attributes") {
      const d = await catalogApi.listAttributes(
        ctx.locale.value,
        search.value,
        page.value,
        20,
        signal,
      );
      return { ...d, items: d.items.map(attributeItem) };
    }
    if (props.kind === "product-types") {
      const d = await catalogApi.listProductTypes(
        ctx.locale.value,
        search.value,
        page.value,
        20,
        signal,
      );
      return { ...d, items: d.items.map(typeItem) };
    }
    const d = await catalogApi.listContentBlocks(
      ctx.locale.value,
      search.value,
      page.value,
      20,
      signal,
    );
    return { ...d, items: d.items.map(blockItem) };
  },
});
const types = useQuery({
  queryKey: computed(() => ctx.key("type-options")),
  enabled: computed(
    () =>
      props.kind === "products" && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  queryFn: ({ signal }) => loadTypes(ctx.locale.value, signal),
});
const readError = computed(() =>
  collection.isError.value
    ? getApiErrorStatus(collection.error.value) === 403
      ? "Нет доступа к каталогу."
      : getApiErrorMessage(
          collection.error.value,
          "Не удалось загрузить данные.",
        )
    : "",
);
function params(values: Record<string, string | number | undefined>) {
  void ctx.router.replace({ query: { ...ctx.route.query, ...values } });
}
function open(item: CollectionItem) {
  void ctx.router.push({
    path: `/catalog/${props.kind}/${item.id}`,
    query: { locale: ctx.locale.value },
  });
}
function create() {
  void ctx.router.push({
    path: `/catalog/${props.kind}/new`,
    query: { locale: ctx.locale.value },
  });
}
async function remove(item: CollectionItem) {
  const current = ctx.captureSession();
  if (pending.value) return;
  if (!window.confirm(`Удалить «${item.label}»?`)) return;
  pending.value = true;
  error.value = "";
  try {
    if (props.kind === "products")
      await catalogApi.deleteProduct(item.id, item.revision);
    else if (props.kind === "product-types")
      await catalogApi.deleteProductType(item.id, item.revision);
    else if (props.kind === "attributes")
      await catalogApi.deleteAttribute(item.id, item.revision);
    else if (props.kind === "tags")
      await catalogApi.deleteTag(item.id, item.revision);
    else await catalogApi.deleteContentBlock(item.id, item.revision);
    if (!current()) return;
    await collection.refetch();
  } catch (e) {
    if (!current()) return;
    error.value = getApiErrorMessage(
      e,
      "Удаление не подтверждено. Обновите список перед повтором.",
    );
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div class="flex min-w-0 flex-col gap-5 p-6">
    <CatalogHeader
      :title="titles[kind]"
      description="Товарная модель и независимые переводы вашего рабочего пространства."
      action="Создать"
      :disabled="!ctx.locale.value || pending || !!readError"
      @create="create"
    /><CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      :types="kind === 'products' ? types.data.value : undefined"
      :type-id="typeId"
      @locale="ctx.selectLocale"
      @type="params({ type: $event || undefined, page: undefined })"
    />
    <label
      v-if="kind === 'products'"
      class="flex flex-wrap items-center gap-2 text-sm"
      >Вид товара
      <select
        aria-label="Вид товара"
        class="rounded-md border bg-background p-2"
        :value="productKind ?? ''"
        @change="
          params({
            kind: ($event.target as HTMLSelectElement).value || undefined,
            page: undefined,
          })
        "
      >
        <option value="">Все виды</option>
        <option value="simple">SIMPLE</option>
        <option value="variable">VARIABLE</option>
      </select>
    </label>
    <p v-if="ctx.locales.isError.value" role="alert">
      Не удалось загрузить локали.
    </p>
    <CatalogSearchBar
      :value="search"
      @search="params({ search: $event || undefined, page: undefined })"
    />
    <p v-if="error" role="alert" class="text-destructive">{{ error }}</p>
    <CatalogCollectionBody
      :selected="!!ctx.locale.value"
      :loading="collection.isPending.value"
      :error="readError"
      :empty="!collection.data.value?.items.length"
      :filtered="!!search || !!typeId || !!productKind"
      @retry="collection.refetch()"
      ><CatalogResults
        :items="collection.data.value?.items ?? []"
        :pending="pending"
        @open="open"
        @delete="remove" /></CatalogCollectionBody
    ><CatalogFooter
      v-if="collection.data.value"
      :page="page"
      :total="collection.data.value.total"
      :page-size="20"
      @page="params({ page: $event })"
    />
  </div>
</template>
