<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { attributeItem, tagItem } from "../../api/catalog.mapper";
import { useCatalogContext } from "../../model/use-catalog-context";
import type { CollectionKind, CollectionItem } from "../../model/catalog.types";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import CatalogSearchBar from "../CatalogSearchBar.vue";
import CatalogResults from "../CatalogResults.vue";
import CatalogCollectionBody from "../CatalogCollectionBody.vue";
import CatalogFooter from "../CatalogFooter.vue";
const props = defineProps<{ kind: CollectionKind }>();
const pending = ref(false),
  error = ref("");
const cache = useQueryClient();
const ctx = useCatalogContext(
  () => false,
  () => pending.value,
);
const search = computed(() => String(ctx.route.query.search ?? "")),
  page = computed(() => Math.max(1, Number(ctx.route.query.page) || 1));
const collection = useQuery({
  queryKey: computed(() =>
    ctx.key("dictionary-list", props.kind, search.value, page.value),
  ),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: async ({ signal }) => {
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
    const d = await catalogApi.listTags(
      ctx.locale.value,
      search.value,
      page.value,
      20,
      signal,
    );
    return { ...d, items: d.items.map(tagItem) };
  },
});
function open(item: CollectionItem) {
  void ctx.router.push({
    path: `/catalog/${props.kind}/${item.id}`,
    query: { locale: ctx.locale.value },
  });
}
async function remove(item: CollectionItem) {
  if (!window.confirm(`Удалить «${item.label}»?`)) return;
  pending.value = true;
  error.value = "";
  try {
    if (props.kind === "attributes")
      await catalogApi.deleteAttribute(item.id, item.revision);
    else await catalogApi.deleteTag(item.id, item.revision);
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
    });
  } catch (e) {
    error.value = getApiErrorMessage(e, "Не удалось выполнить операцию");
  } finally {
    pending.value = false;
  }
}
</script>
<template>
  <div class="min-h-0 min-w-0 flex-1 space-y-5 overflow-y-auto p-6">
    <CatalogHeader
      :title="kind === 'attributes' ? 'Характеристики' : 'Метки'"
      description="Глобальные справочники каталога"
      action="Создать"
      :disabled="pending || !ctx.active.value"
      @create="
        ctx.router.push({
          path: `/catalog/${kind}/new`,
          query: { locale: ctx.locale.value },
        })
      "
    /><CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    /><CatalogSearchBar
      :value="search"
      @search="
        (value) =>
          ctx.router.replace({
            query: { ...ctx.route.query, search: value, page: undefined },
          })
      "
    />
    <p v-if="error || collection.isError.value" role="alert">
      {{
        error ||
        getApiErrorMessage(
          collection.error.value,
          "Не удалось выполнить операцию",
        )
      }}
    </p>
    <CatalogCollectionBody
      :selected="!!ctx.locale.value"
      :loading="collection.isPending.value"
      :error="
        collection.isError.value
          ? getApiErrorMessage(
              collection.error.value,
              'Не удалось выполнить операцию',
            )
          : ''
      "
      :empty="!collection.data.value?.items.length"
      :filtered="!!search"
      @retry="collection.refetch()"
      ><CatalogResults
        :items="collection.data.value?.items ?? []"
        :pending="pending"
        @open="open"
        @delete="remove" /></CatalogCollectionBody
    ><CatalogFooter
      :page="page"
      :total="collection.data.value?.total ?? 0"
      :page-size="20"
      @page="
        (value) =>
          ctx.router.replace({ query: { ...ctx.route.query, page: value } })
      "
    />
  </div>
</template>
