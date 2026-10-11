<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { listItemFromDto } from "../../api/catalog.mapper";
import { useCatalogContext } from "../../model/use-catalog-context";
import type { ItemKind, ItemStatus } from "../../api/catalog.dto";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import CatalogSearchBar from "../CatalogSearchBar.vue";
import CatalogFooter from "../CatalogFooter.vue";
const pending = ref(false),
  error = ref(""),
  cache = useQueryClient();
const ctx = useCatalogContext(
  () => false,
  () => pending.value,
);
const search = computed(() => String(ctx.route.query.search ?? "")),
  page = computed(() => Math.max(1, Number(ctx.route.query.page) || 1)),
  kind = computed(() =>
    ["simple", "variable"].includes(String(ctx.route.query.kind))
      ? (ctx.route.query.kind as ItemKind)
      : undefined,
  ),
  status = computed(() =>
    ["draft", "active", "archived"].includes(String(ctx.route.query.status))
      ? (ctx.route.query.status as ItemStatus)
      : undefined,
  );
const items = useQuery({
  queryKey: computed(() =>
    ctx.key("list-items", search.value, page.value, kind.value, status.value),
  ),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: async ({ signal }) => {
    const d = await catalogApi.listItems(
      ctx.locale.value,
      search.value,
      (page.value - 1) * 20,
      20,
      kind.value,
      status.value,
      signal,
    );
    return { ...d, items: d.items.map(listItemFromDto) };
  },
});
function filter(values: Record<string, string | number | undefined>) {
  void ctx.router.replace({ query: { ...ctx.route.query, ...values } });
}
async function remove(id: string, revision: number, kind: ItemKind) {
  if (!window.confirm("Удалить карточку со всеми её вариантами?")) return;
  pending.value = true;
  error.value = "";
  try {
    const discarded: string[] = [];
    if (kind === "variable") {
      for (let offset = 0; ; offset += 100) {
        const page = await catalogApi.listVariants(
          id,
          ctx.locale.value,
          offset,
          100,
        );
        discarded.push(...page.items.map((v) => v.own.id));
        if (discarded.length >= page.total) break;
      }
    }
    await catalogApi.deleteItem(id, revision, discarded);
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
  <div class="min-w-0 space-y-5 p-6">
    <CatalogHeader
      title="Товары"
      description="Самостоятельные товары и семейства вариантов"
      action="Создать товар"
      :disabled="!ctx.active.value || pending"
      @create="
        ctx.router.push({
          path: '/catalog/items/new',
          query: { locale: ctx.locale.value },
        })
      "
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
        aria-label="Вид товара"
        class="rounded border bg-background p-2"
        :value="kind ?? ''"
        @change="
          filter({
            kind: ($event.target as HTMLSelectElement).value || undefined,
            page: undefined,
          })
        "
      >
        <option value="">Все виды</option>
        <option value="simple">Простой</option>
        <option value="variable">С вариантами</option></select
      ><select
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
            {{ item.kind === "simple" ? "Простой" : "С вариантами" }} ·
            {{ item.status }} · {{ item.sku ?? "Без SKU" }} ·
            {{
              item.price ??
              (item.priceMin
                ? `${item.priceMin}–${item.priceMax}`
                : "Цена не задана")
            }}
          </p></button
        ><Button
          variant="ghost"
          :disabled="pending"
          @click="remove(item.id, item.rootRevision, item.kind)"
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
  </div>
</template>
