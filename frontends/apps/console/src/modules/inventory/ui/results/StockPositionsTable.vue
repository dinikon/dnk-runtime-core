<script setup lang="ts">
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import { Button } from "@/components/ui/button";
import type { StockTrackingColumns } from "../../model/stock-accounting.types";
import type { ListStockPositionsItem } from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
withDefaults(
  defineProps<{
    items: readonly ListStockPositionsItem[];
    columns?: StockTrackingColumns;
  }>(),
  { columns: () => ({ lot: false, serial: false }) },
);
const emit = defineEmits<{ navigate: [target: StockAccountingTarget] }>();
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
          <th class="p-3">Позиция</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" class="border-t">
          <td class="p-3">
            <Button
              variant="link"
              class="h-auto p-0"
              @click="
                emit('navigate', { kind: 'item', id: item.inventoryItemId })
              "
              >{{ item.sku }}</Button
            >
          </td>
          <td class="p-3">
            <Button
              variant="link"
              class="h-auto p-0"
              @click="
                emit('navigate', { kind: 'warehouse', id: item.warehouseId })
              "
              >{{ item.warehouseCode }}</Button
            ><span class="block">{{ item.locationCode }}</span
            ><span
              v-if="!item.warehouseIsActive || !item.locationIsActive"
              class="text-xs text-muted-foreground"
              >Неактивный адрес</span
            >
          </td>
          <td class="p-3">{{ item.ownerName ?? item.ownerId }}</td>
          <td v-if="columns.lot" class="p-3">
            <Button
              v-if="item.lotId"
              variant="link"
              class="h-auto p-0"
              @click="
                emit('navigate', {
                  kind: 'lot',
                  id: item.lotId,
                  itemId: item.inventoryItemId,
                })
              "
              >{{ item.lotNumber }}</Button
            ><span v-else>—</span>
          </td>
          <td v-if="columns.serial" class="p-3">
            <Button
              v-if="item.serialId"
              variant="link"
              class="h-auto p-0"
              @click="
                emit('navigate', {
                  kind: 'serial',
                  id: item.serialId,
                  itemId: item.inventoryItemId,
                })
              "
              >{{ item.serialNumber }}</Button
            ><span v-else>—</span>
          </td>
          <td class="p-3">{{ stockStatusLabel(item.stockStatus) }}</td>
          <td class="whitespace-nowrap p-3 font-medium">
            {{ item.onHandQty }} {{ item.baseUom }}
          </td>
          <td class="p-3">
            <Button
              variant="outline"
              size="sm"
              @click="emit('navigate', { kind: 'position', id: item.id })"
              >Открыть позицию</Button
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
