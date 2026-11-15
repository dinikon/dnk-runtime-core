<script setup lang="ts">
import { stockOperationLabel } from "../../model/stock-accounting.constants";
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import { Button } from "@/components/ui/button";
import type { StockTrackingColumns } from "../../model/stock-accounting.types";
import type { ListStockMovementsItem } from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
withDefaults(
  defineProps<{
    items: readonly ListStockMovementsItem[];
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
          <th class="p-3">Проведено</th>
          <th class="p-3">SKU / адрес</th>
          <th class="p-3">Владелец</th>
          <th v-if="columns.lot" class="p-3">Партия</th>
          <th v-if="columns.serial" class="p-3">Серия</th>
          <th class="p-3">Изменение</th>
          <th class="p-3">Основание</th>
          <th class="p-3">Запись</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" class="border-t">
          <td class="whitespace-nowrap p-3">
            <time :datetime="item.postedAt">{{
              new Date(item.postedAt).toLocaleString()
            }}</time
            ><span class="block text-xs text-muted-foreground">{{
              stockOperationLabel(item.operationType)
            }}</span>
          </td>
          <td class="p-3">
            <Button
              variant="link"
              class="h-auto p-0"
              @click="
                emit('navigate', { kind: 'position', id: item.positionId })
              "
              >{{ item.sku }}</Button
            ><span class="block"
              >{{ item.warehouseCode }} / {{ item.locationCode }}</span
            ><span class="block text-xs">{{
              stockStatusLabel(item.stockStatus)
            }}</span
            ><span
              v-if="item.historicalSkus.some((sku) => sku !== item.sku)"
              class="block text-xs text-muted-foreground"
              >В документе: {{ item.historicalSkus.join(", ") }}</span
            >
          </td>
          <td class="p-3">{{ item.ownerName ?? item.ownerId }}</td>
          <td v-if="columns.lot" class="p-3">{{ item.lotNumber ?? "—" }}</td>
          <td v-if="columns.serial" class="p-3">
            {{ item.serialNumber ?? "—" }}
          </td>
          <td class="whitespace-nowrap p-3 font-medium">
            {{ item.quantityDelta.startsWith("-") ? "" : "+"
            }}{{ item.quantityDelta }} {{ item.baseUom }}
          </td>
          <td class="p-3">
            <div class="flex flex-col items-start gap-1">
              <Button
                variant="link"
                class="h-auto p-0"
                @click="
                  emit('navigate', {
                    kind: 'document',
                    id: item.documentId,
                    operationType: item.operationType,
                  })
                "
                >Документ</Button
              ><Button
                variant="link"
                class="h-auto p-0"
                @click="
                  emit('navigate', { kind: 'execution', id: item.executionId })
                "
                >Исполнение</Button
              ><Button
                variant="link"
                class="h-auto p-0"
                @click="
                  emit('navigate', { kind: 'posting', id: item.postingId })
                "
                >Проводка</Button
              >
            </div>
          </td>
          <td class="max-w-40 break-all p-3 font-mono text-xs">
            {{ item.id
            }}<span class="block font-sans text-muted-foreground"
              >Фактических строк: {{ item.executionLineIds.length }}</span
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
