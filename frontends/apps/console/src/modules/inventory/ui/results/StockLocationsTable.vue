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
import type { StockLocation } from "../../model/stock-location.types";
import { STOCK_LOCATION_TYPE_LABELS } from "../../model/stock-location.constants";
import { stockLocationsColumns } from "./stock-locations.columns";
defineProps<{
  items: readonly StockLocation[];
  defaultLocationId: string | null | undefined;
}>();
const emit = defineEmits<{ edit: [id: string]; children: [id: string] }>();
</script>
<template>
  <TooltipProvider :delay-duration="200"
    ><DataTable
      :rows="items"
      :columns="stockLocationsColumns"
      :row-key="(row) => row.id"
      caption="Локации склада"
      ><template #cell="{ row, column }">
        <Tooltip v-if="column.key === 'code' || column.key === 'name'"
          ><TooltipTrigger as-child
            ><button
              v-if="column.key === 'code'"
              type="button"
              class="block max-w-full truncate text-left font-medium underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :aria-label="`Редактировать локацию ${row.code}`"
              @click="emit('edit', row.id)"
            >
              {{ row.code }}</button
            ><span v-else tabindex="0" class="block truncate">{{
              row.name
            }}</span></TooltipTrigger
          ><TooltipContent
            class="max-w-[min(28rem,calc(100vw-2rem))] break-all"
            >{{ column.key === "code" ? row.code : row.name }}</TooltipContent
          ></Tooltip
        >
        <span v-else-if="column.key === 'locationType'">{{
          STOCK_LOCATION_TYPE_LABELS[row.locationType]
        }}</span>
        <Badge
          v-else-if="column.key === 'isActive'"
          :variant="row.isActive ? 'secondary' : 'outline'"
          >{{ row.isActive ? "Активна" : "Неактивна" }}</Badge
        >
        <template v-else-if="column.key === 'default'"
          ><Badge v-if="row.id === defaultLocationId" variant="secondary"
            >Основная STORAGE</Badge
          ><span v-else class="text-muted-foreground">{{
            defaultLocationId === undefined ? "Загрузка…" : "—"
          }}</span></template
        >
        <div v-else-if="column.key === 'actions'" class="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            :aria-label="`Настройки локации ${row.code}`"
            @click="emit('edit', row.id)"
            >Редактировать</Button
          ><Button
            type="button"
            variant="ghost"
            size="sm"
            :aria-label="`Дочерние локации ${row.code}`"
            @click="emit('children', row.id)"
            >Дочерние</Button
          >
        </div>
      </template></DataTable
    ></TooltipProvider
  >
</template>
