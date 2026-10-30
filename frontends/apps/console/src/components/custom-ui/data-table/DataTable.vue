<script setup lang="ts" generic="TRow extends object, TKey extends string">
import { computed, type CSSProperties, type VNode } from "vue";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { DataTableColumn } from "./data-table.types";

const props = withDefaults(
  defineProps<{
    rows: readonly TRow[];
    columns: readonly DataTableColumn<TKey>[];
    rowKey: (row: TRow) => string;
    caption: string;
    selectedKeys?: readonly string[];
    density?: "default" | "compact";
    isDetailRow?: (row: TRow) => boolean;
  }>(),
  { density: "default" },
);
const emit = defineEmits<{ rowActivate: [row: TRow] }>();
defineSlots<{
  header?(props: { column: DataTableColumn<TKey> }): VNode[];
  cell(props: { row: TRow; column: DataTableColumn<TKey> }): VNode[];
  detail?(props: { row: TRow }): VNode[];
}>();

const width = computed(() =>
  props.columns.reduce((sum, column) => sum + column.width, 0),
);
const flexibleKey = computed(
  () =>
    (
      props.columns.find((column) => column.grow && !column.pinned) ??
      props.columns.find((column) => !column.pinned)
    )?.key,
);
const offsets = computed(() => {
  const result = new Map<TKey, CSSProperties>();
  let start = 0,
    end = 0;
  for (const column of props.columns) {
    if (column.pinned === "start") {
      result.set(column.key, { left: `${start}px` });
      start += column.width;
    }
  }
  for (const column of [...props.columns].reverse()) {
    if (column.pinned === "end") {
      result.set(column.key, { right: `${end}px` });
      end += column.width;
    }
  }
  return result;
});
function alignment(column: DataTableColumn<TKey>): string {
  return column.align === "right"
    ? "text-right"
    : column.align === "center"
      ? "text-center"
      : "text-left";
}
</script>

<template>
  <div
    data-slot="data-table"
    class="flex min-h-0 min-w-0 flex-1 overflow-hidden rounded-lg border [&>[data-slot=table-container]]:min-h-0 [&>[data-slot=table-container]]:min-w-0 [&>[data-slot=table-container]]:flex-1"
  >
    <Table
      :class="
        cn(
          'min-w-[var(--data-table-width)] table-fixed',
          !flexibleKey && 'w-[var(--data-table-width)]',
        )
      "
      :style="{ '--data-table-width': `${width}px` }"
      role="region"
      :aria-label="`${caption}: область прокрутки`"
      tabindex="0"
    >
      <TableCaption class="sr-only">{{ caption }}</TableCaption>
      <colgroup>
        <col
          v-for="column in columns"
          :key="column.key"
          :style="
            column.key === flexibleKey
              ? undefined
              : { width: `${column.width}px` }
          "
        />
      </colgroup>
      <TableHeader class="sticky top-0 z-20 bg-background">
        <TableRow class="hover:bg-background">
          <TableHead
            v-for="column in columns"
            :key="column.key"
            scope="col"
            :style="offsets.get(column.key)"
            :class="
              cn(
                'border-r border-border/60 px-3 last:border-r-0',
                alignment(column),
                column.pinned && 'sticky z-30 bg-background',
              )
            "
          >
            <slot name="header" :column="column">{{ column.label }}</slot>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow
          v-for="row in rows"
          :key="rowKey(row)"
          :data-row-key="rowKey(row)"
          :data-state="
            selectedKeys?.includes(rowKey(row)) ? 'selected' : undefined
          "
          :aria-selected="
            selectedKeys ? selectedKeys.includes(rowKey(row)) : undefined
          "
          :class="cn('group', density === 'compact' ? 'h-8' : 'h-10')"
          @dblclick="!isDetailRow?.(row) && emit('rowActivate', row)"
        >
          <TableCell
            v-if="isDetailRow?.(row)"
            :colspan="columns.length"
            class="px-3 py-2"
          >
            <slot name="detail" :row="row" />
          </TableCell>
          <template v-else>
            <TableCell
              v-for="column in columns"
              :key="column.key"
              :style="offsets.get(column.key)"
              :class="
                cn(
                  'overflow-hidden border-r border-border/60 px-3 last:border-r-0',
                  density === 'compact' ? 'py-0.5' : 'py-1',
                  alignment(column),
                  column.pinned && 'sticky z-10',
                  column.pinned &&
                    (selectedKeys?.includes(rowKey(row))
                      ? 'bg-muted'
                      : 'bg-background group-hover:bg-muted'),
                )
              "
            >
              <slot name="cell" :row="row" :column="column" />
            </TableCell>
          </template>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
