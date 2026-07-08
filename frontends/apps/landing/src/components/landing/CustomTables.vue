<script setup lang="ts">
import { computed, ref } from "vue";
import { Braces, KeyRound, ListPlus, Table2 } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

type Field = {
  name: string;
  type: string;
  role: string;
};

type CustomTable = {
  id: string;
  name: string;
  description: string;
  fields: Field[];
  records: Record<string, string>[];
};

const tables = ref<CustomTable[]>([
  {
    id: "customer-profile",
    name: "crm_customer_profile",
    description:
      "Store tenant-owned attributes that enrich communication rules and provider payloads.",
    fields: [
      { name: "customer_id", type: "uuid", role: "primary key" },
      { name: "intent_score", type: "number", role: "branching" },
      { name: "preferred_channel", type: "enum", role: "routing" },
      { name: "last_purchase_at", type: "datetime", role: "goal context" },
    ],
    records: [
      {
        customer_id: "cus_1028",
        intent_score: "86",
        preferred_channel: "email",
        last_purchase_at: "2026-07-03",
      },
      {
        customer_id: "cus_1172",
        intent_score: "44",
        preferred_channel: "push",
        last_purchase_at: "2026-06-25",
      },
    ],
  },
  {
    id: "goal-ledger",
    name: "workflow_goal_ledger",
    description:
      "Persist goal windows, reached states, and attribution records from workflow execution.",
    fields: [
      { name: "goal_id", type: "text", role: "goal key" },
      { name: "workflow_run_id", type: "uuid", role: "trace" },
      { name: "reached_at", type: "datetime", role: "statistics" },
      { name: "revenue_amount", type: "decimal", role: "attribution" },
    ],
    records: [
      {
        goal_id: "demo_booked",
        workflow_run_id: "run_9238",
        reached_at: "2026-07-05",
        revenue_amount: "0",
      },
      {
        goal_id: "invoice_paid",
        workflow_run_id: "run_9244",
        reached_at: "2026-07-06",
        revenue_amount: "449",
      },
    ],
  },
]);

const fieldSuggestions: Field[] = [
  { name: "consent_status", type: "enum", role: "compliance" },
  { name: "lifetime_value", type: "decimal", role: "segmentation" },
  { name: "locale", type: "text", role: "template locale" },
  { name: "next_best_action", type: "text", role: "workflow input" },
];

const selectedTableId = ref(tables.value[0].id);
const suggestionIndex = ref(0);

const activeTable = computed(
  () => tables.value.find((table) => table.id === selectedTableId.value) ?? tables.value[0],
);

const visibleColumns = computed(() =>
  activeTable.value.fields.slice(0, 4).map((field) => field.name),
);

function selectTable(id: string) {
  selectedTableId.value = id;
}

function addField() {
  const existingNames = new Set(activeTable.value.fields.map((field) => field.name));
  const orderedSuggestions = fieldSuggestions.map((_, index) => {
    const offsetIndex = (suggestionIndex.value + index) % fieldSuggestions.length;
    return fieldSuggestions[offsetIndex];
  });
  const nextField =
    orderedSuggestions.find((field) => !existingNames.has(field.name)) ??
    fieldSuggestions[suggestionIndex.value % fieldSuggestions.length];

  if (!existingNames.has(nextField.name)) {
    activeTable.value.fields.push(nextField);
  }

  suggestionIndex.value = (suggestionIndex.value + 1) % fieldSuggestions.length;
}

function createTable() {
  const existing = tables.value.find((table) => table.id === "retention-actions");

  if (!existing) {
    tables.value.push({
      id: "retention-actions",
      name: "retention_actions",
      description:
        "A tenant-created table for storing custom retention rules used by workflow branches.",
      fields: [
        { name: "rule_id", type: "uuid", role: "primary key" },
        { name: "segment", type: "text", role: "audience" },
        { name: "action", type: "text", role: "workflow node" },
        { name: "priority", type: "number", role: "ordering" },
      ],
      records: [
        {
          rule_id: "rule_018",
          segment: "trial_warm",
          action: "send_demo_offer",
          priority: "1",
        },
        {
          rule_id: "rule_027",
          segment: "dormant_paid",
          action: "start_winback",
          priority: "2",
        },
      ],
    });
  }

  selectedTableId.value = "retention-actions";
}
</script>

<template>
  <section id="tables" class="mx-auto w-full max-w-7xl px-5 py-16 md:px-8">
    <div class="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <h2 class="text-balance text-3xl font-semibold leading-tight sm:text-4xl">
          Create custom tenant tables for workflow data.
        </h2>
        <p class="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
          Product teams can model tenant-specific CRM data without waiting for a
          product deployment. Workflow rules read the tables, write outcomes,
          and keep statistics close to the records that caused them.
        </p>
      </div>

      <Button data-testid="create-table" type="button" class="shrink-0" @click="createTable">
        <ListPlus data-icon="inline-start" aria-hidden="true" />
        Create table
      </Button>
    </div>

    <div class="grid gap-5 lg:grid-cols-[0.72fr_1.28fr]">
      <Card class="rounded-2xl py-5">
        <CardHeader class="px-5">
          <CardTitle class="text-base">Tenant data catalog</CardTitle>
          <CardDescription class="leading-6">
            Tables are scoped to the tenant and available to workflow nodes.
          </CardDescription>
        </CardHeader>
        <CardContent class="grid gap-3 px-5">
          <Button
            v-for="table in tables"
            :key="table.id"
            :data-testid="`table-${table.id}`"
            type="button"
            :variant="selectedTableId === table.id ? 'default' : 'outline'"
            class="h-auto justify-start whitespace-normal rounded-xl px-4 py-3 text-left"
            @click="selectTable(table.id)"
          >
            <span class="grid gap-1">
              <span class="text-sm font-semibold">{{ table.name }}</span>
              <span class="text-xs opacity-80">{{ table.fields.length }} fields</span>
            </span>
          </Button>
        </CardContent>
      </Card>

      <div class="grid gap-5">
        <Card class="rounded-2xl py-5">
          <CardHeader class="px-5">
            <div class="flex flex-col justify-between gap-4 md:flex-row md:items-start">
              <div>
                <CardTitle class="text-xl">{{ activeTable.name }}</CardTitle>
                <CardDescription class="mt-2 max-w-2xl leading-6">
                  {{ activeTable.description }}
                </CardDescription>
              </div>
              <Badge variant="info">tenant schema</Badge>
            </div>
          </CardHeader>
          <CardContent class="grid gap-5 px-5">
            <div class="grid gap-3 md:grid-cols-2">
              <div
                v-for="field in activeTable.fields"
                :key="field.name"
                class="table-field-row rounded-xl border border-border bg-white p-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold">{{ field.name }}</p>
                    <p class="mt-1 text-xs text-muted-foreground">{{ field.role }}</p>
                  </div>
                  <Badge variant="outline">{{ field.type }}</Badge>
                </div>
              </div>
            </div>

            <div class="flex flex-col gap-3 rounded-2xl bg-muted p-4 md:flex-row md:items-center md:justify-between">
              <div class="flex items-center gap-3">
                <div class="flex size-10 items-center justify-center rounded-lg bg-white">
                  <Braces class="size-4 text-sky-600" aria-hidden="true" />
                </div>
                <div>
                  <p class="text-sm font-semibold">Workflow-visible schema</p>
                  <p class="text-xs text-muted-foreground">
                    Branches and provider payloads can use every custom field.
                  </p>
                </div>
              </div>
              <Button data-testid="add-field" type="button" variant="outline" class="bg-white" @click="addField">
                <ListPlus data-icon="inline-start" aria-hidden="true" />
                Add field
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card class="rounded-2xl py-5">
          <CardHeader class="px-5">
            <div class="flex items-center justify-between gap-4">
              <div>
                <CardTitle class="text-base">Data preview</CardTitle>
                <CardDescription class="mt-1">
                  Records stored for the current tenant.
                </CardDescription>
              </div>
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <KeyRound class="size-4" aria-hidden="true" />
                tenant_id scoped
              </div>
            </div>
          </CardHeader>
          <CardContent class="px-5">
            <div class="overflow-x-auto rounded-xl border border-border">
              <table class="min-w-full border-collapse text-left text-sm">
                <thead class="bg-muted text-xs text-muted-foreground">
                  <tr>
                    <th
                      v-for="column in visibleColumns"
                      :key="column"
                      class="whitespace-nowrap px-3 py-3 font-medium"
                    >
                      {{ column }}
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border bg-white">
                  <tr v-for="(record, index) in activeTable.records" :key="index">
                    <td
                      v-for="column in visibleColumns"
                      :key="`${index}-${column}`"
                      class="whitespace-nowrap px-3 py-3"
                    >
                      {{ record[column] ?? "-" }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <Separator class="my-4" />

            <div class="grid gap-3 md:grid-cols-3">
              <div class="flex items-center gap-3 rounded-xl bg-muted p-3">
                <Table2 class="size-4 text-teal-600" aria-hidden="true" />
                <span class="text-xs">Available in conditions</span>
              </div>
              <div class="flex items-center gap-3 rounded-xl bg-muted p-3">
                <Braces class="size-4 text-sky-600" aria-hidden="true" />
                <span class="text-xs">Available in payloads</span>
              </div>
              <div class="flex items-center gap-3 rounded-xl bg-muted p-3">
                <KeyRound class="size-4 text-amber-600" aria-hidden="true" />
                <span class="text-xs">Tenant isolated</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </section>
</template>
