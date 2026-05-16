<script setup lang="ts">
import { computed, watch } from "vue";
import { useQuery } from "@tanstack/vue-query";
import {
  createColumnHelper,
  FlexRender,
  getCoreRowModel,
  useVueTable,
} from "@tanstack/vue-table";
import { Loader2 } from "lucide-vue-next";
import { useRouter } from "vue-router";

import { useSessionStore } from "@/app/stores/session";
import { crmContactsApi, type Contact } from "@/api/crm";
import { getApiErrorMessage, getApiErrorStatus } from "@/api/http/errors";

const router = useRouter();
const sessionStore = useSessionStore();

const contactsQuery = useQuery({
  queryKey: ["crm", "contacts"],
  queryFn: () => crmContactsApi.list(),
});

const contacts = computed(() => contactsQuery.data.value?.items ?? []);
const errorMessage = computed(() =>
  contactsQuery.error.value
    ? getApiErrorMessage(contactsQuery.error.value, "Could not load contacts.")
    : null,
);

const columnHelper = createColumnHelper<Contact>();
const columns = [
  columnHelper.accessor("first_name", {
    header: "First name",
    cell: (info) => formatNullableText(info.getValue()),
  }),
  columnHelper.accessor("last_name", {
    header: "Last name",
    cell: (info) => formatNullableText(info.getValue()),
  }),
  columnHelper.accessor("middle_name", {
    header: "Middle name",
    cell: (info) => formatNullableText(info.getValue()),
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: (info) => formatNullableText(info.getValue()),
  }),
  columnHelper.accessor("tags", {
    header: "Tags",
    cell: (info) => formatTags(info.getValue()),
  }),
  columnHelper.accessor("updated_at", {
    header: "Updated",
    cell: (info) => formatDate(info.getValue()),
  }),
];

const table = useVueTable({
  data: contacts,
  columns,
  getCoreRowModel: getCoreRowModel(),
});

watch(
  () => contactsQuery.error.value,
  async (error) => {
    if (getApiErrorStatus(error) !== 401) {
      return;
    }

    sessionStore.clearSession();
    await router.push("/login");
  },
);

function formatNullableText(value: string | null): string {
  return value?.trim() ? value : "-";
}

function formatTags(tags: string[]): string {
  return tags.length > 0 ? tags.join(", ") : "-";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
</script>

<template>
  <section
    class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm"
  >
    <div
      v-if="errorMessage"
      class="border-b border-red-100 bg-red-50 px-4 py-2 text-sm text-red-700"
    >
      {{ errorMessage }}
    </div>

    <div class="min-h-0 flex-1 overflow-auto">
      <table class="w-full min-w-[960px] border-collapse text-left">
        <thead class="sticky top-0 z-10 bg-white">
          <template
            v-for="headerGroup in table.getHeaderGroups()"
            :key="headerGroup.id"
          >
            <tr
              class="border-b border-neutral-200 text-xs font-semibold text-neutral-500"
            >
              <th
                v-for="header in headerGroup.headers"
                :key="header.id"
                class="border-r border-neutral-100 px-3 py-3 last:border-r-0"
              >
                <FlexRender
                  :render="header.column.columnDef.header"
                  :props="header.getContext()"
                />
              </th>
            </tr>
          </template>
        </thead>

        <tbody>
          <tr v-if="contactsQuery.isLoading.value">
            <td
              :colspan="columns.length"
              class="px-4 py-10 text-center text-sm text-neutral-400"
            >
              <span class="inline-flex items-center gap-2">
                <Loader2 class="size-4 animate-spin" />
                Loading contacts...
              </span>
            </td>
          </tr>

          <tr v-else-if="contacts.length === 0">
            <td
              :colspan="columns.length"
              class="px-4 py-10 text-center text-sm text-neutral-400"
            >
              No contacts found.
            </td>
          </tr>

          <tr
            v-for="row in table.getRowModel().rows"
            v-else
            :key="row.id"
            class="h-11 border-b border-neutral-100 text-sm text-neutral-700"
          >
            <td
              v-for="cell in row.getVisibleCells()"
              :key="cell.id"
              class="max-w-64 truncate border-r border-neutral-100 px-3 py-2 last:border-r-0"
            >
              <FlexRender
                :render="cell.column.columnDef.cell"
                :props="cell.getContext()"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
