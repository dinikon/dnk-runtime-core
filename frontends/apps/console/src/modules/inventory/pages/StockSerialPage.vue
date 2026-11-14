<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useInventoryItemQuery } from "../model/use-inventory-item-query";
import { useStockSerialQuery } from "../model/use-stock-serials-query";
import { StockSerialRequestError } from "../model/stock-serial.errors";
import { InventoryItemsRequestError } from "../model/inventory-item.errors";
import { stockSerialsReturnPath } from "../model/stock-serial-navigation";
import { stockLotLocation } from "../model/stock-lot-navigation";
import StockSerialBody from "../ui/results/StockSerialBody.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const itemId = computed(() =>
  String(route.params.inventoryItemId ?? "").toLowerCase(),
);
const serialId = computed(() =>
  String(route.params.serialId ?? "").toLowerCase(),
);
const query = useStockSerialQuery(itemId, serialId, scope),
  parent = useInventoryItemQuery(itemId, scope);
const inaccessible = computed(() =>
  [query.error.value, parent.error.value].some(
    (error) =>
      (error instanceof StockSerialRequestError ||
        error instanceof InventoryItemsRequestError) &&
      [403, 404].includes(error.status ?? 0),
  ),
);
const serial = computed(() =>
  scope.ready.value && !inaccessible.value ? query.data.value : undefined,
);
const owner = computed(() =>
  scope.ready.value && !inaccessible.value ? parent.data.value : undefined,
);
async function refresh(): Promise<void> {
  if (scope.ready.value) await Promise.all([query.refetch(), parent.refetch()]);
}
function back(): void {
  void router.push(
    stockSerialsReturnPath(itemId.value, route.query.returnTo, true),
  );
}
function lot(id: string): void {
  void router.push(stockLotLocation(itemId.value, id, route.fullPath));
}
</script>
<template>
  <section
    class="flex min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Карточка серийного экземпляра"
  >
    <header class="flex flex-wrap items-start gap-3">
      <Button variant="outline" @click="back">Назад к экземплярам</Button>
      <div class="min-w-0 flex-1">
        <h1 class="text-xl font-semibold">Карточка серийного экземпляра</h1>
        <p v-if="owner" class="break-all font-mono text-sm">{{ owner.sku }}</p>
      </div>
      <Button
        variant="outline"
        :disabled="
          !scope.ready.value ||
          query.isFetching.value ||
          parent.isFetching.value
        "
        @click="refresh"
        >Обновить</Button
      >
    </header>
    <StockSerialBody
      :serial="serial"
      :loading="query.isPending.value && scope.ready.value"
      :refreshing="query.isFetching.value"
      :error="
        scope.error.value ||
        query.error.value?.message ||
        parent.error.value?.message ||
        ''
      "
      @retry="refresh"
      @lot="lot"
    />
  </section>
</template>
