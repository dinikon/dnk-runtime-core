<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import type { CatalogListItem } from "../../model/catalog.types";
import { CATALOG_PAGE_SIZE } from "../../model/catalog-list-state";
import { useCreateCatalogItem } from "../../model/use-create-catalog-item";
import { useCatalogItemsPageState } from "../../model/use-catalog-items-page-state";
import { useCatalogItemsQuery } from "../../model/use-catalog-items-query";
import { useDeleteCatalogItem } from "../../model/use-delete-catalog-item";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogFooter from "../CatalogFooter.vue";
import CatalogItemsToolbar from "../results/CatalogItemsToolbar.vue";
import CatalogItemsBody from "../results/CatalogItemsBody.vue";
import DeleteCatalogItemDialog from "../results/DeleteCatalogItemDialog.vue";
import ProductCreateDialog from "../product/ProductCreateDialog.vue";

const busy = ref(false);
const creation = useCreateCatalogItem(false, () => busy.value);
const { ctx } = creation;
const pageState = useCatalogItemsPageState();
const { params } = pageState;
const items = useCatalogItemsQuery(
  ctx.tenantId,
  ctx.sessionKey,
  ctx.locale,
  params,
);
const deletion = useDeleteCatalogItem(ctx.tenantId, ctx.sessionKey);
const deleteTarget = ref<CatalogListItem | null>(null);
const canCreate = computed(
  () =>
    ctx.active.value && !creation.state.pending && !deletion.isPending.value,
);
const queryError = computed(() =>
  items.isError.value
    ? getApiErrorMessage(items.error.value, "Не удалось загрузить товары")
    : "",
);
const deleteError = computed(() =>
  deletion.isError.value
    ? getApiErrorMessage(deletion.error.value, "Не удалось удалить товар")
    : "",
);

watch(
  deletion.isPending,
  (pending) => {
    busy.value = pending;
  },
  { flush: "sync" },
);
watch(ctx.sessionKey, () => {
  deleteTarget.value = null;
});

function open(id: string, edit = false): void {
  void ctx.router.push({
    path: `/catalog/items/${encodeURIComponent(id)}${edit ? "/edit" : ""}`,
    query: { locale: ctx.locale.value },
  });
}
function imageUrl(item: CatalogListItem): string | undefined {
  return item.primaryImage
    ? catalogApi.imageUrl(item.id, ctx.locale.value, item.primaryImage.id)
    : undefined;
}
function askDelete(item: CatalogListItem): void {
  deletion.reset();
  deleteTarget.value = item;
}
function closeDelete(): void {
  if (deletion.isPending.value) return;
  deleteTarget.value = null;
  deletion.reset();
}
async function remove(): Promise<void> {
  if (!deleteTarget.value || deletion.isPending.value) return;
  const current = ctx.captureSession();
  try {
    await deletion.mutateAsync(deleteTarget.value.id);
    if (!current()) return;
    deleteTarget.value = null;
    if (!items.data.value?.items.length && params.value.page > 1)
      pageState.page(params.value.page - 1);
  } catch {
    // The mutation owns the error; the dialog preserves the selected record for retry.
  }
}
</script>

<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    aria-label="Каталог товаров"
  >
    <CatalogHeader
      title="Товары"
      description="Товары, их цены и наличие"
      action="Создать товар"
      :disabled="!canCreate"
      @create="creation.show"
    >
      <template #actions>
        <Button
          type="button"
          variant="outline"
          :disabled="!ctx.tenantId.value"
          @click="
            ctx.router.push({
              path: '/catalog/imports/new',
              query: { locale: ctx.locale.value },
            })
          "
          >Импортировать позиции</Button
        >
        <Button
          type="button"
          variant="ghost"
          @click="
            ctx.router.push({
              path: '/catalog/imports',
              query: { locale: ctx.locale.value },
            })
          "
          >Журнал импортов</Button
        >
      </template>
    </CatalogHeader>
    <CatalogItemsToolbar
      :search="params.search"
      :status="params.status"
      :locale="ctx.locale.value"
      :locales="ctx.options.value"
      @search="pageState.search"
      @status="pageState.status"
      @locale="ctx.selectLocale"
    />
    <span
      v-if="items.isFetching.value && !items.isPending.value"
      class="sr-only"
      role="status"
      ><Spinner />Обновление товаров</span
    >
    <CatalogItemsBody
      :items="items.data.value?.items ?? []"
      :loading="items.isPending.value"
      :error="queryError"
      :filtered="!!params.search || !!params.status"
      :out-of-range="params.page > 1 && (items.data.value?.total ?? 0) > 0"
      :disabled="deletion.isPending.value"
      :can-create="canCreate"
      :image-url="imageUrl"
      @open="open($event)"
      @edit="open($event, true)"
      @remove="askDelete"
      @retry="items.refetch()"
      @reset="pageState.clear"
      @create="creation.show"
      @first-page="pageState.page(1)"
    />
    <CatalogFooter
      v-if="items.data.value"
      :page="params.page"
      :total="items.data.value.total"
      :page-size="CATALOG_PAGE_SIZE"
      class="shrink-0"
      @page="pageState.page"
    />
    <ProductCreateDialog
      :open="creation.open.value"
      :state="creation.state"
      :disabled="!ctx.active.value"
      @choose="creation.choose"
      @close="creation.close"
      @check="creation.checkCatalog"
    />
    <DeleteCatalogItemDialog
      v-if="deleteTarget"
      :item="deleteTarget"
      :pending="deletion.isPending.value"
      :error="deleteError"
      @close="closeDelete"
      @confirm="remove"
    />
  </section>
</template>
