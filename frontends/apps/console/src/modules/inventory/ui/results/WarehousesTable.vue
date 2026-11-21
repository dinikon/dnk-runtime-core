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
import type { Warehouse } from "../../model/warehouse.types";
import { warehousesColumns } from "./warehouses.columns";
defineProps<{ items: readonly Warehouse[] }>();
const emit = defineEmits<{ edit: [id: string]; locations: [id: string] }>();
</script>
<template>
  <TooltipProvider :delay-duration="200">
    <DataTable
      :rows="items"
      :columns="warehousesColumns"
      :row-key="(row) => row.id"
      caption="Склады"
    >
      <template #cell="{ row, column }">
        <Tooltip v-if="column.key === 'code' || column.key === 'name'">
          <TooltipTrigger as-child>
            <button
              v-if="column.key === 'code'"
              type="button"
              class="block max-w-full truncate text-left font-medium underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :aria-label="`Редактировать склад ${row.code}`"
              @click="emit('edit', row.id)"
            >
              {{ row.code }}
            </button>
            <span v-else tabindex="0" class="block truncate">{{
              row.name
            }}</span>
          </TooltipTrigger>
          <TooltipContent
            class="max-w-[min(28rem,calc(100vw-2rem))] break-all"
            >{{ column.key === "code" ? row.code : row.name }}</TooltipContent
          >
        </Tooltip>
        <Badge
          v-else-if="column.key === 'isActive'"
          :variant="row.isActive ? 'secondary' : 'outline'"
          >{{ row.isActive ? "Активен" : "Неактивен" }}</Badge
        >
        <div v-else-if="column.key === 'actions'" class="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            :aria-label="`Настройки склада ${row.code}`"
            @click="emit('edit', row.id)"
            >Редактировать</Button
          >
          <Button
            type="button"
            variant="ghost"
            size="sm"
            :aria-label="`Локации склада ${row.code}`"
            @click="emit('locations', row.id)"
            >Локации</Button
          >
        </div>
      </template>
    </DataTable>
  </TooltipProvider>
</template>
