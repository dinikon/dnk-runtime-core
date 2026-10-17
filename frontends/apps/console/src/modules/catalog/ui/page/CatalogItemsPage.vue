<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { listItemFromDto } from "../../api/catalog.mapper";
import { useCreateCatalogItem } from "../../model/use-create-catalog-item";
import type { ItemStatus } from "../../api/catalog.dto";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import CatalogSearchBar from "../CatalogSearchBar.vue";
import CatalogFooter from "../CatalogFooter.vue";
import ProductCreateDialog from "../product/ProductCreateDialog.vue";
const pending = ref(false),
  error = ref(""),
  cache = useQueryClient();
const creation = useCreateCatalogItem(false, () => pending.value);
const { ctx } = creation;
const search = computed(() => String(ctx.route.query.search ?? "")),
  page = computed(() => Math.max(1, Number(ctx.route.query.page) || 1)),
  status = computed(() =>
    ["draft", "active", "archived"].includes(String(ctx.route.query.status))
      ? (ctx.route.query.status as ItemStatus)
      : undefined,
  );
const items = useQuery({
  queryKey: computed(() =>
    ctx.key("list-items", search.value, page.value, status.value),
  ),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: async ({ signal }) => {
    const d = await catalogApi.listItems(
      ctx.locale.value,
      search.value,
      (page.value - 1) * 20,
      20,
      status.value,
      signal,
    );
    return { ...d, items: d.items.map(listItemFromDto) };
  },
});
function filter(values: Record<string, string | number | undefined>) {
  void ctx.router.replace({ query: { ...ctx.route.query, ...values } });
}
async function remove(id: string) {
  if (!window.confirm("Удалить товар?")) return;
  pending.value = true;
  error.value = "";
  try {
    await catalogApi.deleteItem(id);
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
      title="Товары"
      description="Товары, их цены и наличие"
      action="Создать товар"
      :disabled="!ctx.active.value || pending"
      @create="creation.show"
    /><CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <div class="flex flex-wrap gap-3">
      <CatalogSearchBar
        :value="search"
        @search="(value) => filter({ search: value, page: undefined })"
      /><select
        aria-label="Статус"
        class="rounded border bg-background p-2"
        :value="status ?? ''"
        @change="
          filter({
            status: ($event.target as HTMLSelectElement).value || undefined,
            page: undefined,
          })
        "
      >
        <option value="">Все статусы</option>
        <option value="draft">Черновик</option>
        <option value="active">Активный</option>
        <option value="archived">Архив</option>
      </select>
    </div>
    <p v-if="error || items.isError.value" role="alert">
      {{
        error ||
        getApiErrorMessage(items.error.value, "Не удалось выполнить операцию")
      }}
    </p>
    <p v-if="items.isPending.value">Загрузка…</p>
    <div class="divide-y rounded-lg border">
      <div
        v-for="item in items.data.value?.items ?? []"
        :key="item.id"
        class="flex flex-wrap items-center justify-between gap-3 p-4"
      >
        <button
          class="min-w-0 text-left"
          @click="
            ctx.router.push({
              path: `/catalog/items/${item.id}`,
              query: { locale: ctx.locale.value },
            })
          "
        >
          <span class="font-medium">{{ item.title ?? "Без перевода" }}</span>
          <p class="text-sm text-muted-foreground">
            {{ item.status }} · {{ item.sku ?? "Без SKU" }} ·
            {{ item.price ?? "Цена не задана" }} {{ item.currency }}
          </p></button
        ><Button variant="ghost" :disabled="pending" @click="remove(item.id)"
          >Удалить</Button
        >
      </div>
      <p
        v-if="!items.isPending.value && !items.data.value?.items.length"
        class="p-8 text-muted-foreground"
      >
        Товары не найдены.
      </p>
    </div>
    <CatalogFooter
      :page="page"
      :total="items.data.value?.total ?? 0"
      :page-size="20"
      @page="(value) => filter({ page: value })"
    />
    <ProductCreateDialog
      :open="creation.open.value"
      :state="creation.state"
      :disabled="!ctx.active.value"
      @choose="creation.choose"
      @close="creation.close"
      @check="creation.checkCatalog"
    />
  </div>
</template>
