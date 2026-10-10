<script setup lang="ts">
import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { useCatalogContext } from "../../model/use-catalog-context";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import CatalogSearchBar from "../CatalogSearchBar.vue";
import CatalogFooter from "../CatalogFooter.vue";
const ctx = useCatalogContext(
  () => false,
  () => false,
  () => {},
);
const parent = computed(() => String(ctx.route.query.parent ?? "")),
  search = computed(() => String(ctx.route.query.search ?? "")),
  page = computed(() => Math.max(1, Number(ctx.route.query.page) || 1));
const branch = useQuery({
  queryKey: computed(() =>
    ctx.key("category-branch", parent.value, search.value, page.value),
  ),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  refetchOnWindowFocus: false,
  queryFn: ({ signal }) =>
    catalogApi.listCategories(
      ctx.locale.value,
      search.value,
      page.value,
      20,
      signal,
      parent.value || undefined,
      !parent.value,
    ),
});
const parentDetails = useQuery({
  queryKey: computed(() => ctx.key("get-category", parent.value)),
  enabled: computed(
    () => !!parent.value && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  queryFn: ({ signal }) =>
    catalogApi.getCategory(parent.value, ctx.locale.value, signal),
});
function params(values: Record<string, string | number | undefined>) {
  void ctx.router.replace({ query: { ...ctx.route.query, ...values } });
}
function enter(id?: string) {
  params({ parent: id, search: undefined, page: undefined });
}
function open(id: string) {
  void ctx.router.push({
    path: `/catalog/categories/${id}`,
    query: { locale: ctx.locale.value },
  });
}
function create() {
  void ctx.router.push({
    path: "/catalog/categories/new",
    query: { locale: ctx.locale.value, parent: parent.value || undefined },
  });
}
</script>
<template>
  <div class="min-w-0 space-y-5 p-6">
    <CatalogHeader
      title="Категории"
      description="Дерево с явными назначениями товаров"
      action="Создать категорию"
      :disabled="
        !ctx.active.value ||
        !!parentDetails.isError.value ||
        !!branch.isError.value
      "
      @create="create"
    />
    <CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <nav class="flex flex-wrap items-center gap-2">
      <Button variant="outline" :disabled="!parent" @click="enter()"
        >Корень дерева</Button
      ><template v-if="parent"
        ><Button
          variant="outline"
          @click="enter(parentDetails.data.value?.parent_id ?? undefined)"
          >На уровень выше</Button
        ><span class="break-all">{{
          parentDetails.data.value?.label ?? parent
        }}</span></template
      >
    </nav>
    <CatalogSearchBar
      :value="search"
      @search="params({ search: $event || undefined, page: undefined })"
    />
    <p v-if="!ctx.locale.value">Выберите locale.</p>
    <p v-else-if="branch.isPending.value">Загрузка ветви…</p>
    <div
      v-else-if="branch.isError.value || parentDetails.isError.value"
      role="alert"
      class="space-y-2"
    >
      <p>
        {{
          getApiErrorMessage(
            branch.error.value ?? parentDetails.error.value,
            "Не удалось загрузить ветвь.",
          )
        }}
      </p>
      <Button
        variant="outline"
        @click="
          branch.refetch();
          parent && parentDetails.refetch();
        "
        >Повторить</Button
      >
    </div>
    <template v-else-if="branch.data.value"
      ><p v-if="!branch.data.value.items.length">
        {{
          search
            ? "В этой ветви совпадений нет."
            : "В этой ветви категорий нет."
        }}
      </p>
      <ul v-else class="divide-y rounded-md border">
        <li
          v-for="c in branch.data.value.items"
          :key="c.id"
          class="flex flex-wrap items-center justify-between gap-3 p-3"
        >
          <div class="min-w-0">
            <p class="break-words font-medium">{{ c.label ?? c.id }}</p>
            <p class="text-sm text-muted-foreground">
              Дочерних категорий: {{ c.child_count }}
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <Button
              variant="outline"
              :aria-label="`Открыть ветвь ${c.label ?? c.id}`"
              @click="enter(c.id)"
              >Открыть ветвь</Button
            ><Button
              variant="ghost"
              :aria-label="`Редактировать ${c.label ?? c.id}`"
              @click="open(c.id)"
              >Редактировать</Button
            >
          </div>
        </li>
      </ul>
      <CatalogFooter
        :page="page"
        :total="branch.data.value.total"
        :page-size="20"
        @page="params({ page: $event })"
    /></template>
  </div>
</template>
