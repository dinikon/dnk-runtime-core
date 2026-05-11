<script setup lang="ts">
import {computed} from "vue";
import {AlertTriangle, Loader2, Table2} from "lucide-vue-next";

import type {ObjectRecord} from "@/api/object-records";
import type {RuntimeField, RuntimeObject} from "@/api/schema-registry";

const props = defineProps<{
  object: RuntimeObject | null;
  fields: RuntimeField[];
  records: ObjectRecord[];
  count: number;
  isLoadingSchema: boolean;
  isLoadingRecords: boolean;
  recordsError: string | null;
}>();

const isLoading = computed(() => props.isLoadingSchema || props.isLoadingRecords);
const tableMinWidth = computed(() => `${Math.max(props.fields.length * 180 + 48, 860)}px`);

function valueFor(record: ObjectRecord, field: RuntimeField): unknown {
  return record.values[field.field_name];
}

function isEmptyValue(value: unknown): boolean {
  return value === null || value === undefined || (Array.isArray(value) && value.length === 0);
}

function optionLabel(field: RuntimeField, value: unknown): string {
  const normalizedValue = String(value);
  return field.options.find((option) => option.value === normalizedValue)?.label ?? normalizedValue;
}

function multiselectLabels(field: RuntimeField, value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((item) => optionLabel(field, item));
}

function formatValue(field: RuntimeField, value: unknown): string {
  if (isEmptyValue(value)) {
    return "";
  }

  if (field.type === "select") {
    return optionLabel(field, value);
  }

  if (field.type === "bool") {
    return value === true ? "Yes" : "No";
  }

  if (field.type === "date") {
    return formatDate(value, false);
  }

  if (field.type === "datetime") {
    return formatDate(value, true);
  }

  if (field.type === "json") {
    return formatJson(value);
  }

  if (field.type === "int" || field.type === "decimal") {
    return formatNumber(value);
  }

  return String(value);
}

function formatDate(value: unknown, includeTime: boolean): string {
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(includeTime
        ? {
          hour: "2-digit",
          minute: "2-digit"
        }
        : {})
  }).format(date);
}

function formatJson(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function formatNumber(value: unknown): string {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? new Intl.NumberFormat("en").format(numericValue) : String(value);
}
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm">
    <header class="flex min-h-14 items-center border-b border-neutral-200 px-4">
      <div class="flex min-w-0 items-center gap-2">
        <Table2 class="size-4 text-neutral-500"/>
        <h1 class="truncate text-sm font-semibold text-neutral-800">
          {{ object?.plural_label ?? "Objects" }} · {{ count }}
        </h1>
      </div>
    </header>

    <div v-if="recordsError"
         class="m-4 flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
      <AlertTriangle class="size-4 shrink-0"/>
      <span>{{ recordsError }}</span>
    </div>

    <div class="min-h-0 flex-1 overflow-auto">
      <div v-if="!object && !isLoading" class="grid h-full place-items-center px-4 text-sm text-neutral-400">
        No object selected.
      </div>

      <table
          v-else
          class="w-full border-collapse text-left"
          :style="{minWidth: tableMinWidth}"
      >
        <thead class="sticky top-0 z-10 bg-white">
        <tr class="border-b border-neutral-200 text-xs font-semibold text-neutral-400">
          <th class="w-12 px-4 py-3">
            <span class="block size-4 rounded border border-neutral-400"/>
          </th>
          <th
              v-for="field in fields"
              :key="field.id"
              class="border-r border-neutral-100 px-3 py-3 align-top last:border-r-0"
          >
            <div class="grid gap-1">
              <span class="truncate text-neutral-500">{{ field.label }}</span>
              <span class="flex min-w-0 items-center gap-1.5">
                  <span
                      class="rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                      :class="field.is_nullable ? 'bg-neutral-100 text-neutral-400' : 'bg-red-50 text-red-600'"
                  >
                    {{ field.is_nullable ? "Optional" : "Required" }}
                  </span>
                  <span class="truncate rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] text-neutral-500">
                    {{ field.type }}
                  </span>
                </span>
            </div>
          </th>
        </tr>
        </thead>

        <tbody>
        <tr v-if="isLoading">
          <td :colspan="Math.max(fields.length + 1, 1)" class="px-4 py-10 text-center text-sm text-neutral-400">
              <span class="inline-flex items-center gap-2">
                <Loader2 class="size-4 animate-spin"/>
                Loading records...
              </span>
          </td>
        </tr>

        <tr v-else-if="fields.length === 0">
          <td class="px-4 py-10 text-center text-sm text-neutral-400">
            This object has no displayable fields.
          </td>
        </tr>

        <tr v-else-if="!recordsError && records.length === 0">
          <td :colspan="fields.length + 1" class="px-4 py-10 text-center text-sm text-neutral-400">
            No records found.
          </td>
        </tr>

        <tr
            v-for="record in records"
            v-else
            :key="record.id"
            class="h-11 border-b border-neutral-100 text-sm text-neutral-700 transition-colors hover:bg-neutral-50"
        >
          <td class="px-4 py-2">
            <span class="block size-4 rounded border border-neutral-500 bg-white"/>
          </td>
          <td
              v-for="field in fields"
              :key="field.id"
              class="max-w-56 truncate border-r border-neutral-100 px-3 py-2 last:border-r-0"
          >
            <span v-if="isEmptyValue(valueFor(record, field))" class="text-neutral-300">—</span>

            <div v-else-if="field.type === 'multiselect'" class="flex min-w-0 flex-wrap gap-1">
                <span
                    v-for="label in multiselectLabels(field, valueFor(record, field))"
                    :key="label"
                    class="rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600"
                >
                  {{ label }}
                </span>
            </div>

            <span
                v-else-if="field.type === 'bool'"
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="valueFor(record, field) === true ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'"
            >
                {{ formatValue(field, valueFor(record, field)) }}
              </span>

            <code v-else-if="field.type === 'uuid'" class="text-xs text-neutral-500">
              {{ formatValue(field, valueFor(record, field)) }}
            </code>

            <span v-else>{{ formatValue(field, valueFor(record, field)) }}</span>
          </td>
        </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
