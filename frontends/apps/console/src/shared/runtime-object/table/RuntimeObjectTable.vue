<script setup lang="ts">
import { computed } from "vue";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Pencil,
  Trash2,
} from "lucide-vue-next";

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
import type {
  RuntimeFieldDescription,
  RuntimeObjectRecord,
  RuntimeSort,
} from "@/shared/runtime-object";

const props = withDefaults(
  defineProps<{
    fields: RuntimeFieldDescription[];
    records: RuntimeObjectRecord[];
    sort: RuntimeSort[];
    isLoading?: boolean;
  }>(),
  {
    isLoading: false,
  },
);

const emit = defineEmits<{
  (event: "sortChange", sort: RuntimeSort[]): void;
  (event: "edit", record: RuntimeObjectRecord): void;
  (event: "delete", record: RuntimeObjectRecord): void;
}>();

const displayFields = computed(() =>
  props.fields
    .filter((field) => field.field_name !== "id")
    .sort((left, right) => fieldWeight(left) - fieldWeight(right)),
);

const columnCount = computed(() => displayFields.value.length + 1);

function fieldWeight(field: RuntimeFieldDescription): number {
  if (field.kind !== "system") {
    return 0;
  }

  if (field.field_name === "created_at") {
    return 10;
  }

  if (field.field_name === "updated_at") {
    return 11;
  }

  return 20;
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

function toggleSort(field: RuntimeFieldDescription) {
  if (!field.sort.enabled) {
    return;
  }

  const index = sortIndex(field);
  const nextSort = [...props.sort];

  if (index === -1) {
    emit("sortChange", [
      ...nextSort,
      { field: field.field_name, direction: "asc" },
    ]);
    return;
  }

  if (nextSort[index].direction === "asc") {
    nextSort.splice(index, 1, {
      field: field.field_name,
      direction: "desc",
    });
    emit("sortChange", nextSort);
    return;
  }

  nextSort.splice(index, 1);
  emit("sortChange", nextSort);
}

function formatValue(
  field: RuntimeFieldDescription,
  record: RuntimeObjectRecord,
): string {
  const value = record[field.field_name];

  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (field.type === "select") {
    const option = field.options.find((item) => item.value === value);
    return option?.label ?? String(value);
  }

  if (field.type === "datetime") {
    const date = new Date(String(value));
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  return String(value);
}

function arrayValue(
  field: RuntimeFieldDescription,
  record: RuntimeObjectRecord,
): string[] {
  const value = record[field.field_name];
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function optionLabel(field: RuntimeFieldDescription, value: string): string {
  return field.options.find((option) => option.value === value)?.label ?? value;
}
</script>

<template>
  <div class="overflow-hidden rounded-lg border">
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead
            v-for="field in displayFields"
            :key="field.field_name"
            class="whitespace-nowrap"
          >
            <Button
              v-if="field.sort.enabled"
              type="button"
              variant="ghost"
              size="sm"
              class="-ml-3 h-8 px-2"
              @click="toggleSort(field)"
            >
              {{ field.label }}
              <ArrowUp v-if="sortDirection(field) === 'asc'" class="size-3.5" />
              <ArrowDown
                v-else-if="sortDirection(field) === 'desc'"
                class="size-3.5"
              />
              <ArrowUpDown v-else class="size-3.5 opacity-50" />
              <Badge
                v-if="sort.length > 1 && sortPriority(field)"
                variant="secondary"
                class="h-5 min-w-5 justify-center px-1 text-[10px]"
              >
                {{ sortPriority(field) }}
              </Badge>
            </Button>
            <span v-else>{{ field.label }}</span>
          </TableHead>
          <TableHead class="sticky right-0 z-10 w-24 bg-background text-right">
            Actions
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <template v-if="isLoading">
          <TableRow v-for="index in 5" :key="index">
            <TableCell v-for="field in displayFields" :key="field.field_name">
              <Skeleton class="h-4 w-28" />
            </TableCell>
            <TableCell>
              <Skeleton class="ml-auto h-8 w-20" />
            </TableCell>
          </TableRow>
        </template>

        <TableEmpty
          v-else-if="records.length === 0"
          :colspan="columnCount"
          class="text-muted-foreground"
        >
          No records found.
        </TableEmpty>

        <TableRow v-for="record in records" v-else :key="record.id">
          <TableCell v-for="field in displayFields" :key="field.field_name">
            <div
              v-if="field.type === 'multiselect'"
              class="flex max-w-64 flex-wrap gap-1"
            >
              <Badge
                v-for="value in arrayValue(field, record)"
                :key="value"
                variant="secondary"
              >
                {{ optionLabel(field, value) }}
              </Badge>
              <span
                v-if="arrayValue(field, record).length === 0"
                class="text-muted-foreground"
              >
                -
              </span>
            </div>
            <span v-else class="line-clamp-2">
              {{ formatValue(field, record) }}
            </span>
          </TableCell>
          <TableCell class="sticky right-0 bg-background">
            <div class="flex justify-end gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                @click="emit('edit', record)"
              >
                <Pencil class="size-4" />
                <span class="sr-only">Edit</span>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                class="text-destructive hover:text-destructive"
                @click="emit('delete', record)"
              >
                <Trash2 class="size-4" />
                <span class="sr-only">Delete</span>
              </Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
