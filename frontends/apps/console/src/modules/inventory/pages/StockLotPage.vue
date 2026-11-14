<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import StockLotBody from "../ui/results/StockLotBody.vue";
import { InventoryItemsRequestError } from "../model/inventory-item.errors";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryItemQuery } from "../model/use-inventory-item-query";
import { useStockLotQuery } from "../model/use-stock-lots-query";
import { stockLotsReturnPath } from "../model/stock-lot-navigation";
import { StockLotRequestError } from "../model/stock-lot.errors";

const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const itemId = computed(() =>
  String(route.params.inventoryItemId ?? "").toLowerCase(),
);
const lotId = computed(() => String(route.params.lotId ?? "").toLowerCase());
const query = useStockLotQuery(itemId, lotId, scope),
  parent = useInventoryItemQuery(itemId, scope);
const inaccessible = computed(
  () =>
    (query.error.value instanceof StockLotRequestError &&
      [403, 404].includes(query.error.value.status ?? 0)) ||
    (parent.error.value instanceof InventoryItemsRequestError &&
      [403, 404].includes(parent.error.value.status ?? 0)),
);
const lot = computed(() =>
  scope.ready.value && !inaccessible.value ? query.data.value : undefined,
);
function back(): void {
  void router.push(
    stockLotsReturnPath(itemId.value, route.query.returnTo, true),
  );
}
async function refresh(): Promise<void> {
  await Promise.all([query.refetch(), parent.refetch()]);
}
</script>
<template>
  <section
    class="flex min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Карточка партии"
  >
    <header class="flex flex-wrap items-start gap-3">
      <Button variant="outline" @click="back">Назад к партиям</Button>
      <div class="min-w-0 flex-1">
        <h1 class="text-xl font-semibold">Карточка партии</h1>
        <p
          v-if="scope.ready.value && !inaccessible"
          class="break-all font-mono text-sm"
        >
          {{ parent.data.value?.sku }}
        </p>
      </div>
      <Button
        variant="outline"
        :disabled="
          query.isFetching.value ||
          parent.isFetching.value ||
          !scope.ready.value
        "
        @click="refresh"
        >Обновить</Button
      >
    </header>
    <StockLotBody
      :lot="lot"
      :loading="query.isPending.value && scope.ready.value"
      :error="
        scope.error.value ||
        query.error.value?.message ||
        parent.error.value?.message ||
        ''
      "
      :refreshing="query.isFetching.value"
      @retry="refresh"
    />
  </section>
</template>
