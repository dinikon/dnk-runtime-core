<script setup lang="ts">
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import { Button } from "@/components/ui/button";
import type {
  ListStockBalancesItem,
  StockTrackingColumns,
} from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
defineProps<{
  items: readonly ListStockBalancesItem[];
  columns: StockTrackingColumns;
}>();
const emit = defineEmits<{
  positions: [row: ListStockBalancesItem];
  navigate: [target: StockAccountingTarget];
}>();
</script>
<template>
  <div class="min-w-0 overflow-x-auto rounded-md border">
    <table class="w-full text-left text-sm">
      <thead>
        <tr>
          <th class="p-3">SKU</th>
          <th class="p-3">Склад / локация</th>
          <th class="p-3">Владелец</th>
          <th v-if="columns.lot" class="p-3">Партия</th>
          <th v-if="columns.serial" class="p-3">Серия</th>
          <th class="p-3">Состояние</th>
          <th class="p-3">Физический остаток</th>
          <th class="p-3">Состав</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in items" :key="row.key" class="border-t">
          <td class="p-3">
            <Button
              variant="link"
              class="h-auto p-0"
              @click="
                emit('navigate', { kind: 'item', id: row.inventoryItemId })
              "
              >{{ row.sku }}</Button
            >
          </td>
          <td class="p-3">
            <Button
              variant="link"
              class="h-auto p-0"
              @click="
                emit('navigate', { kind: 'warehouse', id: row.warehouseId })
              "
              >{{ row.warehouseCode }}</Button
            ><span class="block">{{ row.locationCode }}</span
            ><span
              v-if="!row.warehouseIsActive || !row.locationIsActive"
              class="block text-xs"
              >Неактивный адрес</span
            >
          </td>
          <td class="p-3">{{ row.ownerName ?? row.ownerId }}</td>
          <td v-if="columns.lot" class="p-3">{{ row.lotNumber ?? "—" }}</td>
          <td v-if="columns.serial" class="p-3">
            {{ row.serialNumber ?? "—" }}
          </td>
          <td class="p-3">{{ stockStatusLabel(row.stockStatus) }}</td>
          <td class="whitespace-nowrap p-3 font-medium">
            {{ row.onHandQty }} {{ row.baseUom }}
          </td>
          <td class="p-3">
            <Button variant="outline" size="sm" @click="emit('positions', row)"
              >Позиции ({{ row.positionCount }})</Button
            ><span class="mt-1 block text-xs text-muted-foreground"
              >Партий: {{ row.lotCount }} · серий: {{ row.serialCount }}</span
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
