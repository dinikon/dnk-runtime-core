<script setup lang="ts">
import { computed } from "vue";
import { ArrowDown, ArrowUp, ArrowUpDown, X } from "lucide-vue-next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { BroadcastListItem } from "@/modules/broadcast/api";
import {
  formatBroadcastDate,
  shortBroadcastId,
} from "@/modules/broadcast/util";
import type {
  RuntimeFieldDescription,
  RuntimeSort,
} from "@/shared/runtime-object";

const props = withDefaults(
  defineProps<{
    fields: RuntimeFieldDescription[];
    records: BroadcastListItem[];
    sort: RuntimeSort[];
    isLoading?: boolean;
    isRefreshing?: boolean;
  }>(),
  {
    isLoading: false,
    isRefreshing: false,
  },
);

const emit = defineEmits<{
  (event: "open", record: BroadcastListItem): void;
  (event: "sortChange", sort: RuntimeSort[]): void;
}>();

const preferredOrder = new Map([
  ["title", 0],
  ["status", 1],
  ["description", 2],
  ["created_at", 10],
  ["updated_at", 11],
]);

const displayFields = computed(() =>
  props.fields
    .filter((field) => field.field_name !== "id")
    .sort(
      (left, right) =>
        fieldWeight(left) - fieldWeight(right) ||
        left.label.localeCompare(right.label),
    ),
);
const columnCount = computed(() => displayFields.value.length);
const skeletonRowCount = computed(() =>
  Math.max(8, Math.min(props.records.length || 12, 20)),
);

function fieldWeight(field: RuntimeFieldDescription): number {
  const preferred = preferredOrder.get(field.field_name);

  if (preferred !== undefined) {
    return preferred;
  }

  return field.kind === "system" ? 20 : 5;
}

function sortDirection(
  field: RuntimeFieldDescription,
): RuntimeSort["direction"] | null {
  const index = sortIndex(field);
  return index === -1 ? null : props.sort[index].direction;
}

function sortPriority(field: RuntimeFieldDescription): number | null {
  const index = sortIndex(field);
  return index === -1 ? null : index + 1;
}

function sortIndex(field: RuntimeFieldDescription): number {
  return props.sort.findIndex((item) => item.field === field.field_name);
}

function toggleSort(field: RuntimeFieldDescription, event: MouseEvent) {
  if (!field.sort.enabled) {
    return;
  }

  const index = sortIndex(field);
  const currentDirection = index === -1 ? null : props.sort[index].direction;
  const nextDirection = currentDirection === "asc" ? "desc" : "asc";

  if (!event.shiftKey) {
    emit("sortChange", [{ field: field.field_name, direction: nextDirection }]);
    return;
  }

  if (index === -1) {
    emit("sortChange", [
      ...props.sort,
      { field: field.field_name, direction: "asc" },
    ]);
    return;
  }

  const nextSort = [...props.sort];
  nextSort.splice(index, 1, {
    field: field.field_name,
    direction: nextDirection,
  });
  emit("sortChange", nextSort);
}

function removeSort(field: RuntimeFieldDescription) {
  emit(
    "sortChange",
    props.sort.filter((item) => item.field !== field.field_name),
  );
}

function formatValue(
  field: RuntimeFieldDescription,
  record: BroadcastListItem,
): string {
  const value = record[field.field_name];

  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (field.field_name === "id") {
    return shortBroadcastId(String(value));
  }

  if (field.type === "select") {
    const option = field.options.find((item) => item.value === value);
    return option?.label ?? String(value);
  }

  if (field.type === "datetime") {
    return formatBroadcastDate(String(value));
  }

  return String(value);
}

function columnClass(field: RuntimeFieldDescription) {
  if (field.field_name === "description") {
    return "max-w-[24rem] overflow-hidden";
  }

  if (field.field_name === "created_at" || field.field_name === "updated_at") {
    return "w-48 overflow-hidden";
  }

  if (field.field_name === "status") {
    return "w-36 overflow-hidden";
  }

  return "overflow-hidden";
}

function columnWidth(field: RuntimeFieldDescription): string {
  if (field.field_name === "title") {
    return "22rem";
  }

  if (field.field_name === "description") {
    return "26rem";
  }

  if (field.field_name === "status") {
    return "9rem";
  }

  if (field.field_name === "created_at" || field.field_name === "updated_at") {
    return "12rem";
  }

  return "12rem";
}
</script>

<template>
  <div
    class="relative min-h-0 overflow-hidden rounded-lg border [&>[data-slot=table-container]]:h-full"
    :aria-busy="isLoading || isRefreshing"
  >
    <div
      v-if="isRefreshing"
      class="absolute inset-x-0 top-0 z-30 h-0.5 overflow-hidden bg-primary/10"
    >
      <div class="h-full w-1/3 animate-pulse bg-primary" />
    </div>
    <Table class="min-w-[81rem] table-fixed">
      <colgroup>
        <col
          v-for="field in displayFields"
          :key="field.field_name"
          :style="{ width: columnWidth(field) }"
        />
      </colgroup>
      <TableHeader class="sticky top-0 z-20 bg-background">
        <TableRow>
          <TableHead
            v-for="field in displayFields"
            :key="field.field_name"
            class="whitespace-nowrap"
            :class="columnClass(field)"
          >
            <div v-if="field.sort.enabled" class="-ml-3 flex items-center">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                class="h-8 px-2"
                @click="toggleSort(field, $event)"
              >
                {{ field.label }}
                <ArrowUpDown
                  v-if="!sortDirection(field)"
                  class="size-3.5 opacity-50"
                />
                <Badge
                  v-if="sort.length > 1 && sortPriority(field)"
                  variant="secondary"
                  class="h-5 min-w-5 justify-center px-1 text-[10px]"
                >
                  {{ sortPriority(field) }}
                </Badge>
              </Button>
              <Button
                v-if="sortDirection(field)"
                type="button"
                variant="ghost"
                size="icon"
                class="group h-8 w-8"
                :aria-label="`Remove ${field.label} sort`"
                @click.stop="removeSort(field)"
              >
                <ArrowUp
                  v-if="sortDirection(field) === 'asc'"
                  class="size-3.5 group-hover:hidden"
                />
                <ArrowDown v-else class="size-3.5 group-hover:hidden" />
                <X class="hidden size-3.5 group-hover:block" />
              </Button>
            </div>
            <span v-else>{{ field.label }}</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <template v-if="isLoading">
          <TableRow v-for="index in skeletonRowCount" :key="index">
            <TableCell v-for="field in displayFields" :key="field.field_name">
              <Skeleton class="h-4 w-28" />
            </TableCell>
          </TableRow>
        </template>

        <TableEmpty
          v-else-if="records.length === 0"
          :colspan="columnCount"
          class="text-muted-foreground"
        >
          No broadcasts found.
        </TableEmpty>

        <TableRow
          v-for="(record, index) in records"
          v-else
          :key="record.id"
          role="link"
          tabindex="0"
          :aria-label="`Open broadcast ${record.title}`"
          class="animate-in cursor-pointer fade-in-0 slide-in-from-top-1 duration-300 hover:bg-muted/50"
          :style="{ animationDelay: `${Math.min(index * 20, 180)}ms` }"
          @click="emit('open', record)"
          @keydown.enter="emit('open', record)"
          @keydown.space.prevent="emit('open', record)"
        >
          <TableCell
            v-for="field in displayFields"
            :key="field.field_name"
            :class="columnClass(field)"
          >
            <Badge v-if="field.field_name === 'status'" variant="outline">
              {{ formatValue(field, record) }}
            </Badge>
            <button
              v-else-if="field.field_name === 'title'"
              type="button"
              class="line-clamp-2 text-left font-medium text-primary hover:underline"
              @click.stop="emit('open', record)"
            >
              {{ formatValue(field, record) }}
            </button>
            <span v-else class="line-clamp-2">
              {{ formatValue(field, record) }}
            </span>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
