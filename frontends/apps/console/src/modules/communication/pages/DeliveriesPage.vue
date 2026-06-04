<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { ArrowDown, ArrowUp, Eye, RefreshCcw, Search } from "lucide-vue-next";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { communicationApi } from "@/modules/communication/api";
import type { OutboundMessage } from "@/modules/communication/api";
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";
import StatusBadge from "@/modules/communication/components/StatusBadge.vue";
import { apiErrorMessage } from "@/modules/communication/lib";

type SortDirection = "asc" | "desc";
type SortField =
  | "created_at"
  | "updated_at"
  | "queued_at"
  | "sent_at"
  | "delivered_at"
  | "failed_at"
  | "internal_status"
  | "channel_code"
  | "recipient_address"
  | "external_status";

const SORT_OPTIONS: { field: SortField; label: string }[] = [
  { field: "created_at", label: "Created" },
  { field: "updated_at", label: "Updated" },
  { field: "queued_at", label: "Queued" },
  { field: "sent_at", label: "Sent" },
  { field: "delivered_at", label: "Delivered" },
  { field: "failed_at", label: "Failed" },
  { field: "internal_status", label: "Status" },
  { field: "channel_code", label: "Channel" },
  { field: "recipient_address", label: "Recipient" },
  { field: "external_status", label: "Provider status" },
];

const PAGE_SIZES = [25, 50, 100, 200];

const search = ref("");
const statusFilter = ref("ALL");
const channelFilter = ref("ALL");
const sortField = ref<SortField>("created_at");
const sortDirection = ref<SortDirection>("desc");
const pageSize = ref(50);
const offset = ref(0);
const detailOpen = ref(false);
const activeMessage = ref<OutboundMessage | null>(null);

const messagesQuery = useQuery({
  queryKey: computed(() => [
    "communication",
    "outbound-messages",
    pageSize.value,
    offset.value,
  ]),
  queryFn: () =>
    communicationApi.listOutboundMessages({
      limit: pageSize.value,
      offset: offset.value,
    }),
  retry: false,
});

const messages = computed(() => messagesQuery.data.value?.items ?? []);
const statusOptions = computed(() =>
  uniqueOptions(messages.value.map((message) => message.internal_status)),
);
const channelOptions = computed(() =>
  uniqueOptions(messages.value.map((message) => message.channel_code)),
);
const visibleMessages = computed(() => {
  const query = search.value.trim().toLowerCase();

  return messages.value
    .filter((message) => {
      if (
        statusFilter.value !== "ALL" &&
        message.internal_status !== statusFilter.value
      ) {
        return false;
      }

      if (
        channelFilter.value !== "ALL" &&
        message.channel_code !== channelFilter.value
      ) {
        return false;
      }

      if (!query) {
        return true;
      }

      return searchableMessageText(message).includes(query);
    })
    .slice()
    .sort((left, right) => compareMessages(left, right));
});
const currentPage = computed(
  () => Math.floor(offset.value / pageSize.value) + 1,
);
const canGoPrevious = computed(() => offset.value > 0);
const canGoNext = computed(() => messages.value.length === pageSize.value);

function uniqueOptions(values: string[]) {
  return Array.from(new Set(values.filter(Boolean))).sort((left, right) =>
    left.localeCompare(right),
  );
}

function searchableMessageText(message: OutboundMessage) {
  return [
    message.outbound_message_id,
    message.communication_request_id,
    message.provider_connection_id,
    message.channel_code,
    message.recipient_identifier_type,
    message.recipient_address,
    message.external_message_id,
    message.external_status,
    message.internal_status,
    message.error_code,
    message.error_message,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function compareMessages(left: OutboundMessage, right: OutboundMessage) {
  const leftValue = left[sortField.value];
  const rightValue = right[sortField.value];
  const direction = sortDirection.value === "asc" ? 1 : -1;

  if (leftValue === rightValue) {
    return 0;
  }

  if (leftValue === null || leftValue === undefined) {
    return 1;
  }

  if (rightValue === null || rightValue === undefined) {
    return -1;
  }

  return String(leftValue).localeCompare(String(rightValue)) * direction;
}

function toggleSortDirection() {
  sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
}

function setPageSize(event: Event) {
  const target = event.target;

  if (!(target instanceof HTMLSelectElement)) {
    return;
  }

  pageSize.value = Number(target.value);
  offset.value = 0;
}

function goPrevious() {
  offset.value = Math.max(0, offset.value - pageSize.value);
}

function goNext() {
  offset.value += pageSize.value;
}

function resetFilters() {
  search.value = "";
  statusFilter.value = "ALL";
  channelFilter.value = "ALL";
  sortField.value = "created_at";
  sortDirection.value = "desc";
}

function openDetails(message: OutboundMessage) {
  activeMessage.value = message;
  detailOpen.value = true;
}

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function shortId(value: string) {
  return value.slice(0, 8);
}

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between"
    >
      <CommunicationPageHeader
        title="Deliveries"
        description="Search, filter, sort, inspect, and page through outbound communication messages and provider statuses."
      />
      <Button
        type="button"
        variant="outline"
        :disabled="messagesQuery.isFetching.value"
        @click="messagesQuery.refetch()"
      >
        <RefreshCcw
          class="size-4"
          :class="{ 'animate-spin': messagesQuery.isFetching.value }"
        />
        Refresh
      </Button>
    </div>

    <Alert v-if="messagesQuery.error.value" variant="destructive">
      <AlertDescription>
        {{ apiErrorMessage(messagesQuery.error.value) }}
      </AlertDescription>
    </Alert>

    <div class="grid shrink-0 gap-3 rounded-lg border p-3">
      <div
        class="grid gap-3 xl:grid-cols-[minmax(16rem,1fr)_12rem_12rem_12rem_auto_auto]"
      >
        <div class="relative">
          <Search
            class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input v-model="search" class="pl-9" placeholder="Search messages" />
        </div>

        <select
          v-model="statusFilter"
          class="border-input bg-background h-9 rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <option value="ALL">All statuses</option>
          <option v-for="status in statusOptions" :key="status" :value="status">
            {{ status }}
          </option>
        </select>

        <select
          v-model="channelFilter"
          class="border-input bg-background h-9 rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <option value="ALL">All channels</option>
          <option
            v-for="channel in channelOptions"
            :key="channel"
            :value="channel"
          >
            {{ channel }}
          </option>
        </select>

        <select
          v-model="sortField"
          class="border-input bg-background h-9 rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <option
            v-for="option in SORT_OPTIONS"
            :key="option.field"
            :value="option.field"
          >
            {{ option.label }}
          </option>
        </select>

        <Button type="button" variant="outline" @click="toggleSortDirection">
          <ArrowUp v-if="sortDirection === 'asc'" class="size-4" />
          <ArrowDown v-else class="size-4" />
          {{ sortDirection.toUpperCase() }}
        </Button>

        <Button type="button" variant="outline" @click="resetFilters">
          Reset
        </Button>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-auto rounded-lg border">
      <Table>
        <TableHeader class="sticky top-0 z-10 bg-background">
          <TableRow>
            <TableHead>Status</TableHead>
            <TableHead>Channel</TableHead>
            <TableHead>Recipient</TableHead>
            <TableHead>Provider status</TableHead>
            <TableHead>External ID</TableHead>
            <TableHead>Queued</TableHead>
            <TableHead>Sent</TableHead>
            <TableHead>Delivered</TableHead>
            <TableHead>Failed</TableHead>
            <TableHead>Updated</TableHead>
            <TableHead class="text-right">Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="message in visibleMessages"
            :key="message.outbound_message_id"
            class="cursor-pointer"
            @click="openDetails(message)"
          >
            <TableCell>
              <StatusBadge :status="message.internal_status" />
            </TableCell>
            <TableCell>
              <Badge variant="secondary">{{ message.channel_code }}</Badge>
            </TableCell>
            <TableCell class="min-w-56">
              <div class="grid gap-1">
                <span class="text-sm font-medium">
                  {{ message.recipient_address }}
                </span>
                <span class="text-xs text-muted-foreground">
                  {{ message.recipient_identifier_type }}
                </span>
              </div>
            </TableCell>
            <TableCell>
              <span class="text-sm">
                {{ message.external_status ?? "-" }}
              </span>
            </TableCell>
            <TableCell class="font-mono text-xs">
              {{ message.external_message_id ?? "-" }}
            </TableCell>
            <TableCell class="whitespace-nowrap text-sm">
              {{ formatDate(message.queued_at) }}
            </TableCell>
            <TableCell class="whitespace-nowrap text-sm">
              {{ formatDate(message.sent_at) }}
            </TableCell>
            <TableCell class="whitespace-nowrap text-sm">
              {{ formatDate(message.delivered_at) }}
            </TableCell>
            <TableCell class="whitespace-nowrap text-sm">
              {{ formatDate(message.failed_at) }}
            </TableCell>
            <TableCell class="whitespace-nowrap text-sm">
              {{ formatDate(message.updated_at) }}
            </TableCell>
            <TableCell class="text-right">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                @click.stop="openDetails(message)"
              >
                <Eye class="size-4" />
                <span class="sr-only">
                  Open {{ shortId(message.outbound_message_id) }}
                </span>
              </Button>
            </TableCell>
          </TableRow>
          <TableRow
            v-if="
              !messagesQuery.isLoading.value && visibleMessages.length === 0
            "
          >
            <TableCell
              colspan="11"
              class="h-24 text-center text-muted-foreground"
            >
              No messages match the current query.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-center md:justify-between"
    >
      <div class="flex flex-wrap items-center gap-3">
        <p class="text-sm text-muted-foreground">
          Page {{ currentPage }} · showing {{ visibleMessages.length }} of
          {{ messages.length }} loaded
        </p>
        <div class="flex items-center gap-2">
          <span class="text-sm text-muted-foreground">Rows</span>
          <select
            :value="String(pageSize)"
            class="border-input bg-background h-8 rounded-md border px-2 text-sm shadow-xs outline-none"
            @change="setPageSize"
          >
            <option
              v-for="size in PAGE_SIZES"
              :key="size"
              :value="String(size)"
            >
              {{ size }}
            </option>
          </select>
        </div>
      </div>
      <div class="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="!canGoPrevious || messagesQuery.isFetching.value"
          @click="goPrevious"
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="!canGoNext || messagesQuery.isFetching.value"
          @click="goNext"
        >
          Next
        </Button>
      </div>
    </div>

    <Dialog v-model:open="detailOpen">
      <DialogContent class="max-h-[90svh] overflow-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Delivery details</DialogTitle>
          <DialogDescription>
            {{ activeMessage?.outbound_message_id }}
          </DialogDescription>
        </DialogHeader>
        <div v-if="activeMessage" class="grid gap-4">
          <div class="grid gap-3 md:grid-cols-3">
            <div class="grid gap-1 rounded-md border p-3">
              <span class="text-xs text-muted-foreground">Status</span>
              <StatusBadge :status="activeMessage.internal_status" />
            </div>
            <div class="grid gap-1 rounded-md border p-3">
              <span class="text-xs text-muted-foreground">Channel</span>
              <span class="text-sm font-medium">{{
                activeMessage.channel_code
              }}</span>
            </div>
            <div class="grid gap-1 rounded-md border p-3">
              <span class="text-xs text-muted-foreground">Provider status</span>
              <span class="text-sm font-medium">
                {{ activeMessage.external_status ?? "-" }}
              </span>
            </div>
          </div>

          <div class="grid gap-1">
            <h3 class="text-sm font-semibold">Recipient snapshot</h3>
            <pre class="overflow-auto rounded-md bg-muted p-3 text-xs">{{
              prettyJson(activeMessage.recipient_snapshot)
            }}</pre>
          </div>

          <div class="grid gap-1">
            <h3 class="text-sm font-semibold">Rendered payload</h3>
            <pre class="overflow-auto rounded-md bg-muted p-3 text-xs">{{
              prettyJson(activeMessage.rendered_payload)
            }}</pre>
          </div>

          <div class="grid gap-1">
            <h3 class="text-sm font-semibold">Provider request payload</h3>
            <pre class="overflow-auto rounded-md bg-muted p-3 text-xs">{{
              prettyJson(activeMessage.provider_request_payload)
            }}</pre>
          </div>

          <Alert v-if="activeMessage.error_message" variant="destructive">
            <AlertDescription>
              {{ activeMessage.error_code }}: {{ activeMessage.error_message }}
            </AlertDescription>
          </Alert>
        </div>
      </DialogContent>
    </Dialog>
  </section>
</template>
