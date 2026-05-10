<script setup lang="ts">
import {ChevronDown, List, Loader2, Plus} from "lucide-vue-next";

import type {ContactTableLabels, ContactTableRow} from "@/components/app/table/types";

defineProps<{
  rows: ContactTableRow[];
  selectedKey: string | null;
  isLoading: boolean;
  count: number;
  labels: ContactTableLabels;
}>();

defineEmits<{
  select: [row: ContactTableRow];
  create: [];
}>();

function contactName(row: ContactTableRow): string {
  const name = [row.firstName, row.lastName].filter(Boolean).join(" ").trim();
  return name || (row.isDraft ? "Untitled contact" : "No name");
}

function formatDate(value: string | null): string {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date(value));
}
</script>

<template>
  <section class="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm">
    <header class="flex min-h-14 items-center border-b border-neutral-200 px-4">
      <div class="flex min-w-0 items-center gap-2">
        <List class="size-4 text-neutral-500"/>
        <h1 class="truncate text-sm font-semibold text-neutral-800">All Contacts · {{ count }}</h1>
        <ChevronDown class="size-4 text-neutral-400"/>
      </div>

      <div class="ml-auto flex items-center gap-3 text-sm font-medium text-neutral-500">
        <button class="hover:text-neutral-900" type="button">Filter</button>
        <button class="hover:text-neutral-900" type="button">Sort</button>
        <button class="hover:text-neutral-900" type="button">Options</button>
        <button
            class="ml-2 inline-flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-sm font-medium text-neutral-700 shadow-sm transition-colors hover:bg-neutral-50"
            type="button"
            @click="$emit('create')"
        >
          <Plus class="size-4"/>
          New Record
        </button>
      </div>
    </header>

    <div class="min-h-0 flex-1 overflow-auto">
      <table class="w-full min-w-[820px] table-fixed border-collapse text-left">
        <thead class="sticky top-0 z-10 bg-white">
        <tr class="border-b border-neutral-200 text-xs font-semibold text-neutral-400">
          <th class="w-10 px-4 py-3">
            <span class="block size-4 rounded border border-neutral-400"/>
          </th>
          <th class="w-[28%] border-r border-neutral-100 px-3 py-3">{{ labels.name }}</th>
          <th class="w-[16%] border-r border-neutral-100 px-3 py-3">{{ labels.status }}</th>
          <th class="w-[24%] border-r border-neutral-100 px-3 py-3">{{ labels.tags }}</th>
          <th class="w-[16%] border-r border-neutral-100 px-3 py-3">{{ labels.createdAt }}</th>
          <th class="w-[16%] px-3 py-3">{{ labels.updatedAt }}</th>
        </tr>
        </thead>
        <tbody>
        <tr v-if="isLoading">
          <td colspan="6" class="px-4 py-10 text-center text-sm text-neutral-400">
              <span class="inline-flex items-center gap-2">
                <Loader2 class="size-4 animate-spin"/>
                Loading contacts...
              </span>
          </td>
        </tr>

        <tr v-else-if="rows.length === 0">
          <td colspan="6" class="px-4 py-10 text-center text-sm text-neutral-400">
            No contacts yet. Create the first record.
          </td>
        </tr>

        <tr
            v-for="row in rows"
            v-else
            :key="row.key"
            class="h-11 cursor-pointer border-b border-neutral-100 text-sm text-neutral-700 transition-colors hover:bg-neutral-50"
            :class="selectedKey === row.key ? 'bg-neutral-100/80' : ''"
            @click="$emit('select', row)"
        >
          <td class="px-4 py-2">
            <span class="block size-4 rounded border border-neutral-500 bg-white"/>
          </td>
          <td class="truncate border-r border-neutral-100 px-3 py-2">
              <span
                  class="inline-flex max-w-full items-center rounded bg-neutral-100 px-2 py-0.5 font-medium text-neutral-800"
                  :class="row.isDraft ? 'text-neutral-400' : ''"
              >
                {{ contactName(row) }}
              </span>
          </td>
          <td class="truncate border-r border-neutral-100 px-3 py-2">
              <span v-if="row.status" class="rounded-full border border-neutral-200 px-2 py-0.5 text-xs capitalize">
                {{ row.status }}
              </span>
          </td>
          <td class="truncate border-r border-neutral-100 px-3 py-2">
            <div class="flex min-w-0 flex-wrap gap-1">
                <span
                    v-for="tag in row.tags"
                    :key="tag"
                    class="rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600"
                >
                  {{ tag }}
                </span>
            </div>
          </td>
          <td class="truncate border-r border-neutral-100 px-3 py-2 text-neutral-500">
            {{ formatDate(row.createdAt) }}
          </td>
          <td class="truncate px-3 py-2 text-neutral-500">{{ formatDate(row.updatedAt) }}</td>
        </tr>
        </tbody>
      </table>
    </div>

    <footer class="min-h-12 border-t border-neutral-100 px-[76px] py-3 text-sm text-neutral-400">
      {{ isLoading ? "Loading more..." : "Calculate" }}
    </footer>
  </section>
</template>
