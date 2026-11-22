<script setup lang="ts">
import {
  DataTable,
  type DataTableColumn,
} from "@/components/custom-ui/data-table";
import { Button } from "@/components/ui/button";
import { MoreHorizontal, Settings2, Archive } from "@lucide/vue";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import type { FeedListItem } from "../../model/feed.types";
import FeedStatus from "../item/FeedStatus.vue";
defineProps<{ items: FeedListItem[]; busy: boolean }>();
defineEmits<{ open: [id: string]; archive: [feed: FeedListItem] }>();
const columns: readonly DataTableColumn<
  "name" | "code" | "format" | "status" | "fields" | "updated" | "actions"
>[] = [
  { key: "name", label: "Название", width: 220, grow: true },
  { key: "code", label: "Код", width: 180 },
  { key: "format", label: "Формат", width: 90 },
  { key: "status", label: "Статус", width: 150 },
  { key: "fields", label: "Поля", width: 70 },
  { key: "updated", label: "Обновлён", width: 180 },
  { key: "actions", label: "Действия", width: 56, align: "right" },
];
</script>
<template>
  <DataTable
    :rows="items"
    :columns="columns"
    :row-key="(row) => row.id"
    caption="Фиды"
    class="max-h-[65dvh] lg:max-h-none"
    @row-activate="$emit('open', $event.id)"
  >
    <template #header="{ column }"
      ><span v-if="column.key === 'actions'" class="sr-only">Действия</span
      ><template v-else>{{ column.label }}</template></template
    >
    <template #cell="{ row, column }">
      <button
        v-if="column.key === 'name'"
        type="button"
        class="block w-full truncate text-left font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :title="row.name"
        @click="$emit('open', row.id)"
      >
        {{ row.name }}
      </button>
      <span
        v-else-if="column.key === 'code'"
        class="block truncate text-muted-foreground"
        :title="row.code"
        >{{ row.code }}</span
      >
      <span v-else-if="column.key === 'format'">{{
        row.format.toUpperCase()
      }}</span>
      <FeedStatus v-else-if="column.key === 'status'" :status="row.status" />
      <span v-else-if="column.key === 'fields'">{{ row.fieldsCount }}</span>
      <time
        v-else-if="column.key === 'updated'"
        :datetime="row.updatedAt"
        class="whitespace-nowrap text-muted-foreground"
        >{{ new Date(row.updatedAt).toLocaleString("ru-RU") }}</time
      >
      <DropdownMenu v-else-if="column.key === 'actions'">
        <DropdownMenuTrigger as-child
          ><Button
            variant="ghost"
            size="icon-sm"
            :disabled="busy"
            :aria-label="`Действия: ${row.name}`"
            ><MoreHorizontal /></Button
        ></DropdownMenuTrigger>
        <DropdownMenuContent align="end"
          ><DropdownMenuGroup>
            <DropdownMenuItem @select="$emit('open', row.id)"
              ><Settings2 />Настройки</DropdownMenuItem
            >
            <DropdownMenuItem
              v-if="row.status !== 'ARCHIVED'"
              variant="destructive"
              @select="$emit('archive', row)"
              ><Archive />В архив</DropdownMenuItem
            >
          </DropdownMenuGroup></DropdownMenuContent
        >
      </DropdownMenu>
    </template>
  </DataTable>
</template>
