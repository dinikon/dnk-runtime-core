<script setup lang="ts">
import { watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useReceiptsQuery } from "../model/use-receipts-query";
import { useReceiptPageState } from "../model/use-receipt-page-state";
import { useReceiptLookups } from "../model/use-receipt-lookups";
import ReceiptDocumentsToolbar from "../ui/page/ReceiptDocumentsToolbar.vue";
import ReceiptDocumentsBody from "../ui/results/ReceiptDocumentsBody.vue";
import ReceiptDocumentsFooter from "../ui/page/ReceiptDocumentsFooter.vue";
import ReceiptReferencePicker from "../ui/forms/ReceiptReferencePicker.vue";
const scope = useInventoryScope(),
  state = useReceiptPageState(),
  query = useReceiptsQuery(state.params, scope),
  router = useRouter(),
  route = useRoute(),
  lookup = useReceiptLookups(scope, false);
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
    name: "inventory-receipt-document",
    params: { documentId: id },
    query: { returnTo: route.fullPath },
  });
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Поступления"
  >
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Поступления</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Плановые документы приёмки. Создание черновика не меняет остатки.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          variant="outline"
          :disabled="!scope.ready.value || query.isFetching.value"
          @click="query.refetch()"
          >Обновить</Button
        ><Button
          :disabled="!scope.ready.value"
          @click="router.push({ name: 'inventory-receipt-create' })"
          >Создать поступление</Button
        >
      </div>
    </header>
    <ReceiptDocumentsToolbar
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
        <ReceiptReferencePicker
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
        /><ReceiptReferencePicker
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
    <ReceiptDocumentsBody
      :page="query.data.value"
      :loading="query.isPending.value"
      :refreshing="query.isFetching.value"
      :error="scope.error.value || query.error.value?.message || ''"
      :ready="scope.ready.value"
      @retry="query.refetch()"
      @open="open"
    /><ReceiptDocumentsFooter
      v-if="query.data.value && scope.ready.value"
      :offset="state.params.value.offset"
      :limit="state.params.value.limit"
      :total="query.data.value.total"
      :pending="query.isFetching.value"
      @page="state.page"
    />
  </section>
</template>
