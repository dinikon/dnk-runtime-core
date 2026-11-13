<script setup lang="ts">
import { DataTable } from "@/components/custom-ui/data-table";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ItemPackaging } from "../../model/item-packaging.types";
import { itemPackagingsColumns } from "./item-packagings.columns";
defineProps<{ items: readonly ItemPackaging[] }>();
const emit = defineEmits<{ edit: [id: string] }>();
</script>
<template>
  <TooltipProvider :delay-duration="200"
    ><DataTable
      :rows="items"
      :columns="itemPackagingsColumns"
      :row-key="(row) => row.id"
      caption="Упаковки SKU"
    >
      <template #cell="{ row, column }">
        <Tooltip v-if="column.key !== 'actions'"
          ><TooltipTrigger as-child>
            <button
              v-if="column.key === 'code'"
              type="button"
              class="block max-w-full truncate text-left font-medium underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :aria-label="`Редактировать упаковку ${row.code}`"
              @click="emit('edit', row.id)"
            >
              {{ row.code }}
            </button>
            <span v-else tabindex="0" class="block truncate">{{
              row[column.key]
            }}</span> </TooltipTrigger
          ><TooltipContent
            class="max-w-[min(28rem,calc(100vw-2rem))] break-all"
            >{{ row[column.key] }}</TooltipContent
          ></Tooltip
        >
        <Button
          v-else
          type="button"
          variant="outline"
          size="sm"
          :aria-label="`Настройки упаковки ${row.code}`"
          @click="emit('edit', row.id)"
          >Редактировать</Button
        >
      </template>
    </DataTable></TooltipProvider
  >
</template>
