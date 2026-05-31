<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Check,
  Minus,
  Pencil,
  Trash2,
  X,
} from "lucide-vue-next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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

const selectedRecordIds = ref(new Set<string>());

const visibleRecordIds = computed(() =>
  props.records.map((record) => record.id),
);
const selectedVisibleRecordIds = computed(() =>
  visibleRecordIds.value.filter((id) => selectedRecordIds.value.has(id)),
);
const headerSelectionState = computed<boolean | "indeterminate">(() => {
  if (visibleRecordIds.value.length === 0) {
    return false;
  }

  if (selectedVisibleRecordIds.value.length === visibleRecordIds.value.length) {
    return true;
  }

  return selectedVisibleRecordIds.value.length > 0 ? "indeterminate" : false;
});
const columnCount = computed(() => displayFields.value.length + 2);
const skeletonRowCount = computed(() =>
  Math.max(8, Math.min(props.records.length || 12, 20)),
);

watch(
  visibleRecordIds,
  (nextIds) => {
    const nextVisibleIds = new Set(nextIds);
    selectedRecordIds.value = new Set(
      [...selectedRecordIds.value].filter((id) => nextVisibleIds.has(id)),
    );
  },
  { immediate: true },
);

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

function isRecordSelected(record: RuntimeObjectRecord): boolean {
  return selectedRecordIds.value.has(record.id);
}

function toggleAllRows(value: boolean | "indeterminate") {
  selectedRecordIds.value =
    value === true ? new Set(visibleRecordIds.value) : new Set();
}

function toggleRow(
  record: RuntimeObjectRecord,
  value: boolean | "indeterminate",
) {
  const nextSelectedIds = new Set(selectedRecordIds.value);

  if (value === true) {
    nextSelectedIds.add(record.id);
  } else {
    nextSelectedIds.delete(record.id);
  }

  selectedRecordIds.value = nextSelectedIds;
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
  <div
    class="min-h-0 overflow-hidden rounded-lg border [&>[data-slot=table-container]]:h-full"
  >
    <Table>
      <TableHeader class="sticky top-0 z-20 bg-background">
        <TableRow>
          <TableHead class="w-10">
            <Checkbox
              :model-value="headerSelectionState"
              :disabled="isLoading || records.length === 0"
              aria-label="Select all rows"
              @update:model-value="toggleAllRows"
            >
              <template #default="{ state }">
                <Minus v-if="state === 'indeterminate'" class="size-3.5" />
                <Check v-else class="size-3.5" />
              </template>
            </Checkbox>
          </TableHead>
          <TableHead
            v-for="field in displayFields"
            :key="field.field_name"
            class="whitespace-nowrap"
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
          <TableHead class="sticky right-0 z-10 w-24 bg-background text-right">
            Actions
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <template v-if="isLoading">
          <TableRow v-for="index in skeletonRowCount" :key="index">
            <TableCell class="w-10">
              <Skeleton class="size-4" />
            </TableCell>
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

        <TableRow
          v-for="(record, index) in records"
          v-else
          :key="record.id"
          :data-state="isRecordSelected(record) ? 'selected' : undefined"
          class="animate-in fade-in-0 slide-in-from-top-1 duration-300"
          :style="{ animationDelay: `${Math.min(index * 20, 180)}ms` }"
        >
          <TableCell class="w-10">
            <Checkbox
              :model-value="isRecordSelected(record)"
              :aria-label="`Select row ${index + 1}`"
              @update:model-value="(value) => toggleRow(record, value)"
            />
          </TableCell>
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
