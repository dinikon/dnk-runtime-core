<script setup lang="ts">
import { computed, ref, toRef, watch } from "vue";
import { Button } from "@/components/ui/button";
import { OffsetPagination } from "@/shared/pagination";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { getApiErrorMessage } from "@/app/providers/http";
import { useCatalogContext } from "../../model/use-catalog-context";
import {
  useCatalogVariants,
  useCatalogVariantMutations,
} from "../../model/use-catalog-variants";
import { useCatalogVariantsPageState } from "../../model/use-catalog-variants-page-state";
import CatalogVariantsList from "../product/CatalogVariantsList.vue";
import DeleteCatalogVariantDialog from "../product/DeleteCatalogVariantDialog.vue";
import CatalogVariantEditorPage from "./CatalogVariantEditorPage.vue";
import type { ProductStock } from "../../model/product.types";
const props = defineProps<{ rootId: string; parentStock: ProductStock }>();
const ctx = useCatalogContext(),
  rootId = toRef(props, "rootId");
const state = useCatalogVariantsPageState(rootId, ctx.locale);
const query = useCatalogVariants(
  rootId,
  ctx.tenantId,
  ctx.sessionKey,
  ctx.locale,
  state.pagination,
);
const actions = useCatalogVariantMutations(
  rootId,
  ctx.tenantId,
  ctx.sessionKey,
);
const deleting = ref<string | null>(null);
const deleteTitle = computed(
  () =>
    query.data.value?.items.find((v) => v.id === deleting.value)?.title ??
    deleting.value ??
    "",
);
watch([rootId, ctx.sessionKey], () => {
  deleting.value = null;
});
async function add(): Promise<void> {
  const id = await actions.create();
  if (id) state.open(id);
}
async function remove(): Promise<void> {
  const target = deleting.value;
  if (target && (await actions.remove(target))) deleting.value = null;
}
async function reload(): Promise<void> {
  const result = await query.refetch();
  if (!result.isError) actions.reset();
}
</script>
<template>
  <section class="flex min-w-0 flex-col gap-4" aria-label="Варианты карточки">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-lg font-semibold">
        Варианты{{ query.data.value ? " · " + query.data.value.total : "" }}
      </h2>
      <Button
        :disabled="actions.pending.value || actions.uncertain.value"
        @click="add"
        >Добавить вариант</Button
      >
    </div>
    <Alert v-if="actions.error.value && !deleting" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-3"
        >{{ actions.error.value
        }}<Button
          variant="outline"
          :disabled="actions.pending.value"
          @click="reload"
          >Обновить список</Button
        ></AlertDescription
      ></Alert
    >
    <CatalogVariantsList
      :items="query.data.value?.items ?? []"
      :pending="query.isPending.value"
      :error="
        query.error.value
          ? getApiErrorMessage(
              query.error.value,
              'Не удалось загрузить варианты.',
            )
          : ''
      "
      :disabled="actions.pending.value"
      @open="state.open"
      @remove="deleting = $event"
      @retry="reload"
    />
    <OffsetPagination
      v-if="query.data.value"
      :page="
        Math.floor(
          state.pagination.value.offset / state.pagination.value.limit,
        ) + 1
      "
      :limit="state.pagination.value.limit"
      :limit-options="[25, 50, 100]"
      :total="query.data.value.total"
      locale="ru"
      @change="state.setPage"
    />
    <CatalogVariantEditorPage
      v-if="state.selected.value"
      :key="`${ctx.sessionKey.value}:${rootId}:${state.selected.value}`"
      :variant-id="state.selected.value"
      :parent-stock="parentStock"
      @close="state.close"
    />
    <DeleteCatalogVariantDialog
      :open="!!deleting"
      :title="deleteTitle"
      :pending="actions.pending.value"
      :error="actions.error.value"
      @update:open="!$event && (deleting = null)"
      @confirm="remove"
    />
  </section>
</template>
