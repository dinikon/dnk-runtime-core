<script setup lang="ts">
import { ref, watch, useId } from "vue";
import { Search, Settings2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { CompaniesExampleParams } from "../../model/companies-example.types";
import {
  companiesExampleColumns,
  type CompaniesExampleColumn,
} from "./companies-example.columns";

const props = defineProps<{
  params: CompaniesExampleParams;
  compact: boolean;
  hidden: readonly CompaniesExampleColumn[];
}>();
const emit = defineEmits<{
  update: [patch: Partial<CompaniesExampleParams>];
  compact: [value: boolean];
  toggleColumn: [key: CompaniesExampleColumn];
}>();
const search = ref(props.params.search),
  id = useId();
watch(
  () => props.params.search,
  (value) => {
    search.value = value;
  },
);
</script>

<template>
  <div class="flex shrink-0 flex-wrap items-center justify-between gap-3">
    <form
      class="flex w-full min-w-0 items-center gap-2 sm:max-w-xs"
      role="search"
      @submit.prevent="emit('update', { search })"
    >
      <FieldGroup class="min-w-0 flex-1"
        ><Field
          ><FieldLabel :for="id" class="sr-only">Search companies</FieldLabel
          ><Input
            :id="id"
            v-model="search"
            placeholder="Company or website…" /></Field
      ></FieldGroup>
      <Button
        type="submit"
        variant="outline"
        size="icon"
        aria-label="Search companies"
        ><Search
      /></Button>
    </form>
    <div class="flex flex-wrap items-center gap-2">
      <Select
        :model-value="params.icp"
        @update:model-value="
          emit('update', { icp: $event as CompaniesExampleParams['icp'] })
        "
        ><SelectTrigger class="w-36" aria-label="Filter ICP"
          ><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem value="all">All companies</SelectItem
            ><SelectItem value="true">ICP · True</SelectItem
            ><SelectItem value="false">ICP · False</SelectItem></SelectGroup
          ></SelectContent
        ></Select
      >
      <Select
        :model-value="params.sort"
        @update:model-value="
          emit('update', { sort: $event as CompaniesExampleParams['sort'] })
        "
        ><SelectTrigger class="w-40" aria-label="Sort companies"
          ><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem value="original">Original order</SelectItem
            ><SelectItem value="name">Name · A–Z</SelectItem
            ><SelectItem value="arr-desc"
              >ARR · High to low</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      >
      <DropdownMenu
        ><DropdownMenuTrigger as-child
          ><Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="Table options"
            ><Settings2 /></Button></DropdownMenuTrigger
        ><DropdownMenuContent align="end" class="w-52">
          <DropdownMenuGroup
            ><DropdownMenuCheckboxItem
              :model-value="compact"
              @select.prevent
              @update:model-value="emit('compact', $event)"
              >Compact rows</DropdownMenuCheckboxItem
            ></DropdownMenuGroup
          >
          <DropdownMenuSeparator />
          <DropdownMenuGroup
            ><DropdownMenuLabel>Visible columns</DropdownMenuLabel
            ><DropdownMenuCheckboxItem
              v-for="column in companiesExampleColumns.filter(
                (column) => column.key !== 'selection',
              )"
              :key="column.key"
              :model-value="!hidden.includes(column.key)"
              :disabled="column.key === 'name'"
              @select.prevent
              @update:model-value="emit('toggleColumn', column.key)"
              >{{ column.label }}</DropdownMenuCheckboxItem
            ></DropdownMenuGroup
          >
        </DropdownMenuContent></DropdownMenu
      >
    </div>
  </div>
</template>
