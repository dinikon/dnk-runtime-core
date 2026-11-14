<script setup lang="ts">
import { DataTable } from "@/components/custom-ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  inventoryExpirationLabels,
  inventoryTrackingLabels,
} from "../../model/inventory-item.constants";
import type { InventoryItemListRow } from "../../model/inventory-item.types";
import { inventoryItemsColumns } from "./inventory-items.columns";

defineProps<{ items: readonly InventoryItemListRow[]; disabled?: boolean }>();
const emit = defineEmits<{
  edit: [id: string];
  packagings: [id: string];
  delete: [item: InventoryItemListRow];
}>();
</script>

<template>
  <TooltipProvider :delay-duration="200">
    <DataTable
      :rows="items"
      :columns="inventoryItemsColumns"
      :row-key="(row) => row.id"
      caption="Складская номенклатура"
    >
      <template #cell="{ row, column }">
        <Tooltip v-if="column.key === 'sku' || column.key === 'quantityStep'">
          <TooltipTrigger as-child>
            <button
              v-if="column.key === 'sku'"
              type="button"
              class="block max-w-full truncate text-left font-medium underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :disabled="disabled"
              :aria-label="`Редактировать SKU ${row.sku}`"
              @click="emit('edit', row.id)"
            >
              {{ row.sku }}
            </button>
            <span
              v-else
              tabindex="0"
              class="block truncate font-mono tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >{{ row.quantityStep }}</span
            >
          </TooltipTrigger>
          <TooltipContent
            class="max-w-[min(28rem,calc(100vw-2rem))] break-all font-mono"
            >{{
              column.key === "sku" ? row.sku : row.quantityStep
            }}</TooltipContent
          >
        </Tooltip>
        <div v-else-if="column.key === 'actions'" class="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="disabled"
            :aria-label="`Редактировать ${row.sku}`"
            @click="emit('edit', row.id)"
            >Редактировать</Button
          >
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="disabled"
            :aria-label="`Упаковки SKU ${row.sku}`"
            @click="emit('packagings', row.id)"
            >Упаковки</Button
          >
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="disabled"
            :aria-label="`Удалить SKU ${row.sku}`"
            @click="emit('delete', row)"
            >Удалить</Button
          >
        </div>
        <span v-else-if="column.key === 'baseUom'" class="font-mono text-sm">{{
          row.baseUom
        }}</span>
        <span
          v-else-if="
            column.key === 'trackingMode' && row.trackingMode === 'NONE'
          "
          class="text-muted-foreground"
          >{{ inventoryTrackingLabels[row.trackingMode] }}</span
        >
        <Badge v-else-if="column.key === 'trackingMode'" variant="outline">{{
          inventoryTrackingLabels[row.trackingMode]
        }}</Badge>
        <Badge
          v-else-if="
            column.key === 'expirationMode' && row.expirationMode === 'REQUIRED'
          "
          variant="secondary"
          >{{ inventoryExpirationLabels[row.expirationMode] }}</Badge
        >
        <span
          v-else-if="column.key === 'expirationMode'"
          class="text-muted-foreground"
          >{{ inventoryExpirationLabels[row.expirationMode] }}</span
        >
      </template>
    </DataTable>
  </TooltipProvider>
</template>
