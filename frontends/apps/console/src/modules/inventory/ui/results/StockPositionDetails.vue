<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import type { GetStockPositionResult } from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
defineProps<{ position: GetStockPositionResult }>();
const emit = defineEmits<{ navigate: [target: StockAccountingTarget] }>();
</script>
<template>
  <section v-if="position" class="shrink-0 rounded-lg border p-4">
    <h2 class="text-lg font-semibold">{{ position.sku }}</h2>
    <p class="my-3 text-2xl font-semibold">
      {{ position.onHandQty }} {{ position.baseUom }}
    </p>
    <dl class="grid gap-4 text-sm sm:grid-cols-2">
      <div>
        <dt class="text-muted-foreground">Склад / локация</dt>
        <dd>
          {{ position.warehouseCode }} — {{ position.warehouseName }} /
          {{ position.locationCode
          }}<span
            v-if="!position.warehouseIsActive || !position.locationIsActive"
            class="block"
            >Адрес неактивен; история сохранена.</span
          >
        </dd>
      </div>
      <div>
        <dt class="text-muted-foreground">Владелец</dt>
        <dd>{{ position.ownerName ?? position.ownerId }}</dd>
      </div>
      <div>
        <dt class="text-muted-foreground">Партия / серия</dt>
        <dd>
          {{ position.lotNumber ?? "—" }} / {{ position.serialNumber ?? "—" }}
        </dd>
      </div>
      <div>
        <dt class="text-muted-foreground">Состояние / версия</dt>
        <dd>
          {{ stockStatusLabel(position.stockStatus) }} ·
          {{ position.version }}
        </dd>
      </div>
      <div>
        <dt class="text-muted-foreground">Даты из партии</dt>
        <dd>
          {{ position.manufacturedOn ?? "—" }} /
          {{ position.expiresOn ?? "—" }}
        </dd>
      </div>
      <div>
        <dt class="text-muted-foreground">Сумма всей истории Ledger</dt>
        <dd>{{ position.ledgerQuantity }} {{ position.baseUom }}</dd>
      </div>
    </dl>
    <div class="mt-4 flex flex-wrap gap-2">
      <Button
        variant="outline"
        @click="
          emit('navigate', { kind: 'item', id: position.inventoryItemId })
        "
        >SKU</Button
      ><Button
        variant="outline"
        @click="
          emit('navigate', { kind: 'warehouse', id: position.warehouseId })
        "
        >Склад</Button
      ><Button
        v-if="position.lotId"
        variant="outline"
        @click="
          emit('navigate', {
            kind: 'lot',
            id: position.lotId,
            itemId: position.inventoryItemId,
          })
        "
        >Партия</Button
      ><Button
        v-if="position.serialId"
        variant="outline"
        @click="
          emit('navigate', {
            kind: 'serial',
            id: position.serialId,
            itemId: position.inventoryItemId,
          })
        "
        >Серийный экземпляр</Button
      >
    </div>
  </section>
</template>
