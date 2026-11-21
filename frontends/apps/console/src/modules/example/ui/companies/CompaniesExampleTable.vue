<script setup lang="ts">
import { computed } from "vue";
import { Check, Minus, X } from "@lucide/vue";
import {
  DataTable,
  type DataTableColumn,
} from "@/components/custom-ui/data-table";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import type { ExampleCompany } from "../../model/companies-example.types";
import type { CompaniesExampleColumn } from "./companies-example.columns";

const props = defineProps<{
  rows: readonly ExampleCompany[];
  columns: readonly DataTableColumn<CompaniesExampleColumn>[];
  selected: readonly string[];
  compact: boolean;
}>();
const emit = defineEmits<{
  select: [id: string, checked: boolean];
  selectAll: [checked: boolean];
}>();
const allSelected = computed(
  () =>
    props.rows.length > 0 &&
    props.rows.every((row) => props.selected.includes(row.id)),
);
const someSelected = computed(() =>
  props.rows.some((row) => props.selected.includes(row.id)),
);
const logos = import.meta.glob<string>("../../assets/companies/*.svg", {
  eager: true,
  query: "?url",
  import: "default",
});
const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}
</script>

<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    :row-key="(row) => row.id"
    :selected-keys="selected"
    :density="compact ? 'compact' : 'default'"
    caption="Company records"
  >
    <template #header="{ column }">
      <Checkbox
        v-if="column.key === 'selection'"
        aria-label="Select all companies"
        :model-value="
          allSelected ? true : someSelected ? 'indeterminate' : false
        "
        @update:model-value="emit('selectAll', $event === true)"
        ><Minus v-if="someSelected && !allSelected" class="size-3.5" /><Check
          v-else
          class="size-3.5"
      /></Checkbox>
      <span v-else>{{ column.label }}</span>
    </template>
    <template #cell="{ row, column }">
      <Checkbox
        v-if="column.key === 'selection'"
        :aria-label="`Select ${row.name}`"
        :model-value="selected.includes(row.id)"
        @update:model-value="emit('select', row.id, $event === true)"
      />
      <Badge
        v-else-if="column.key === 'name'"
        variant="entity"
        class="max-w-full gap-1.5"
        ><img
          :src="logos[`../../assets/companies/${row.id}.svg`]"
          alt=""
          class="size-4 shrink-0 object-contain"
        /><span class="truncate">{{ row.name }}</span></Badge
      >
      <Badge
        v-else-if="column.key === 'domain'"
        variant="link"
        as="a"
        :href="`https://${row.domain}`"
        target="_blank"
        rel="noopener noreferrer"
        class="max-w-full"
        ><span class="truncate">{{ row.domain }}</span></Badge
      >
      <span
        v-else-if="column.key === 'owner' || column.key === 'creator'"
        class="inline-flex max-w-full items-center gap-1.5"
        :title="row[column.key]"
        ><Avatar class="size-5"
          ><AvatarFallback
            ><span class="text-[8px]">{{
              initials(row[column.key])
            }}</span></AvatarFallback
          ></Avatar
        ><span class="truncate">{{ row[column.key] }}</span></span
      >
      <span
        v-else-if="column.key === 'icp'"
        class="inline-flex items-center gap-1.5"
        ><Check v-if="row.icp" class="size-4" aria-hidden="true" /><X
          v-else
          class="size-4"
          aria-hidden="true"
        />{{ row.icp ? "True" : "False" }}</span
      >
      <span v-else-if="column.key === 'arr'" class="tabular-nums">{{
        currency.format(row.arr)
      }}</span>
      <Badge
        v-else-if="column.key === 'linkedin'"
        variant="link"
        as="a"
        :href="`https://www.linkedin.com/company/${row.linkedin}`"
        target="_blank"
        rel="noopener noreferrer"
        class="max-w-full"
        ><span class="truncate">{{ row.linkedin }}</span></Badge
      >
      <span
        v-else-if="column.key === 'address'"
        class="block truncate"
        :title="row.address"
        >{{ row.address }}</span
      >
    </template>
  </DataTable>
</template>
