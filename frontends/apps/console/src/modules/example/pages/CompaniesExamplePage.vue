<script setup lang="ts">
import { computed, ref } from "vue";
import { Building2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/custom-ui/empty-state";
import { exampleCompanies } from "../model/companies-example.constants";
import { selectExampleCompanies } from "../model/companies-example.selectors";
import { useCompaniesExamplePageState } from "../model/use-companies-example-page-state";
import {
  companiesExampleColumns,
  type CompaniesExampleColumn,
} from "../ui/companies/companies-example.columns";
import CompaniesExampleTable from "../ui/companies/CompaniesExampleTable.vue";
import CompaniesExampleToolbar from "../ui/companies/CompaniesExampleToolbar.vue";

const { params, update, reset } = useCompaniesExamplePageState();
const rows = computed(() =>
  selectExampleCompanies(exampleCompanies, params.value),
);
const selected = ref<string[]>([]),
  compact = ref(false),
  hidden = ref<CompaniesExampleColumn[]>([]);
const columns = computed(() =>
  companiesExampleColumns.filter(
    (column) => !hidden.value.includes(column.key),
  ),
);
function select(id: string, checked: boolean): void {
  selected.value = checked
    ? [...new Set([...selected.value, id])]
    : selected.value.filter((key) => key !== id);
}
function selectAll(checked: boolean): void {
  const visible = new Set(rows.value.map((row) => row.id));
  selected.value = checked
    ? [...new Set([...selected.value, ...visible])]
    : selected.value.filter((key) => !visible.has(key));
}
function toggleColumn(key: CompaniesExampleColumn): void {
  if (key === "name" || key === "selection") return;
  hidden.value = hidden.value.includes(key)
    ? hidden.value.filter((value) => value !== key)
    : [...hidden.value, key];
}
</script>

<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    aria-label="Companies example"
  >
    <header class="flex shrink-0 flex-wrap items-center justify-between gap-3">
      <div class="flex flex-col gap-1">
        <h1 class="flex items-center gap-2 text-xl font-semibold">
          <Building2 class="size-5 text-info" aria-hidden="true" />Companies
        </h1>
        <p class="text-sm text-muted-foreground">
          Companies, their owners and annual revenue.
        </p>
      </div>
      <span class="text-sm text-muted-foreground"
        >All Companies · {{ rows.length }}</span
      >
    </header>
    <CompaniesExampleToolbar
      :params="params"
      :compact="compact"
      :hidden="hidden"
      @update="update"
      @compact="compact = $event"
      @toggle-column="toggleColumn"
    />
    <div v-if="selected.length" class="flex shrink-0 items-center gap-3">
      <span class="text-sm text-muted-foreground"
        >{{ selected.length }} selected</span
      ><Button type="button" variant="ghost" size="sm" @click="selected = []"
        >Clear selection</Button
      >
    </div>
    <CompaniesExampleTable
      v-if="rows.length"
      :rows="rows"
      :columns="columns"
      :selected="selected"
      :compact="compact"
      @select="select"
      @select-all="selectAll"
    />
    <div v-else class="min-h-0 flex-1 overflow-auto">
      <EmptyState
        :icon="Building2"
        title="No companies found"
        description="Try another search or clear the ICP filter."
        primary-action-label="Reset filters"
        @primary-action="reset"
      />
    </div>
  </section>
</template>
