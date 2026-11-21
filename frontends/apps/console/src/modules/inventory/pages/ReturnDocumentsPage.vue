<script setup lang="ts">
import { watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useReturnsQuery } from "../model/use-returns-query";
import { useReturnPageState } from "../model/use-return-page-state";
import { useReturnLookups } from "../model/use-return-lookups";
import ReturnDocumentsToolbar from "../ui/page/ReturnDocumentsToolbar.vue";
import ReturnDocumentsBody from "../ui/results/ReturnDocumentsBody.vue";
import ReturnDocumentsFooter from "../ui/page/ReturnDocumentsFooter.vue";
import ReturnReferencePicker from "../ui/forms/ReturnReferencePicker.vue";
const scope = useInventoryScope(),
  state = useReturnPageState(),
  query = useReturnsQuery(state.params, scope),
  router = useRouter(),
  route = useRoute(),
  lookup = useReturnLookups(scope, false);
watch(
  () => query.data.value,
  (p) => {
    if (
      p &&
      state.params.value.offset >= p.total &&
      state.params.value.offset > 0
    )
      state.page(Math.max(0, Math.floor((p.total - 1) / p.limit) * p.limit));
  },
);
function open(id: string): void {
  void router.push({
    name: "inventory-return-document",
    params: { documentId: id },
    query: { returnTo: route.fullPath },
  });
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Возвраты"
  >
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Возвраты</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Создавайте возврат из карточки исходного исполнения поступления или
          расхода. Черновик не меняет остатки.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          variant="outline"
          :disabled="!scope.ready.value || query.isFetching.value"
          @click="query.refetch()"
          >Обновить</Button
        >
      </div>
    </header>
    <ReturnDocumentsToolbar
      :params="state.params.value"
      :disabled="!scope.ready.value"
      @change="state.change"
    />
    <details class="rounded-md border p-3">
      <summary class="cursor-pointer text-sm font-medium">
        Склад и владелец<span
          v-if="state.params.value.warehouseId || state.params.value.ownerId"
        >
          — фильтры включены</span
        >
      </summary>
      <div class="mt-4 grid gap-5 lg:grid-cols-2">
        <ReturnReferencePicker
          label="Склад"
          :search="lookup.warehouses.search.value"
          :items="lookup.warehouses.items.value"
          :selected-id="state.params.value.warehouseId"
          :loading="lookup.warehouses.loading.value"
          :error="lookup.warehouses.error.value"
          :offset="lookup.warehouses.offset.value"
          :total="lookup.warehouses.total.value"
          :disabled="!scope.ready.value"
          allow-clear
          @search="lookup.warehouses.setSearch"
          @select="state.change({ warehouseId: $event.id })"
          @page="lookup.warehouses.page"
          @retry="lookup.warehouses.retry"
          @clear="state.change({ warehouseId: undefined })"
        /><ReturnReferencePicker
          label="Компания-владелец"
          :search="lookup.owners.search.value"
          :items="lookup.owners.items.value"
          :selected-id="state.params.value.ownerId"
          :loading="lookup.owners.loading.value"
          :error="lookup.owners.error.value"
          :offset="lookup.owners.offset.value"
          :total="lookup.owners.total.value"
          :disabled="!scope.ready.value"
          allow-clear
          @search="lookup.owners.setSearch"
          @select="state.change({ ownerId: $event.id })"
          @page="lookup.owners.page"
          @retry="lookup.owners.retry"
          @clear="state.change({ ownerId: undefined })"
        />
      </div>
    </details>
    <ReturnDocumentsBody
      :page="query.data.value"
      :loading="query.isPending.value"
      :refreshing="query.isFetching.value"
      :error="scope.error.value || query.error.value?.message || ''"
      :ready="scope.ready.value"
      @retry="query.refetch()"
      @open="open"
    /><ReturnDocumentsFooter
      v-if="query.data.value && scope.ready.value"
      :offset="state.params.value.offset"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :pending="query.isFetching.value"
      @page="state.page"
    />
  </section>
</template>
