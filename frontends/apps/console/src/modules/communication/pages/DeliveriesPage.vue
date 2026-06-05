<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  getCoreRowModel,
  getFilteredRowModel,
  useVueTable,
  type ColumnDef,
} from "@tanstack/vue-table";
import { Eye, RefreshCcw, SendHorizontal } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";

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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
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
import { Textarea } from "@/components/ui/textarea";
import type {
  JsonObject,
  MessageTemplate,
  OutboundMessage,
} from "@/modules/communication/api";
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";
import DeliveriesToolBar from "@/modules/communication/components/DeliveriesToolBar.vue";
import StatusBadge from "@/modules/communication/components/StatusBadge.vue";
import {
  apiErrorMessage,
  createClientUuid,
  formatJsonObject,
  parseJsonObject,
} from "@/modules/communication/lib";
import { useSendCommunicationMutation } from "@/modules/communication/mutations/use-send-communication-mutation";
import { useMessageTemplatesQuery } from "@/modules/communication/queries/use-message-templates-query";
import { useOutboundMessagesQuery } from "@/modules/communication/queries/use-outbound-messages-query";

const PAGE_SIZE = 50;

const route = useRoute();
const router = useRouter();

const offset = ref(0);
const detailOpen = ref(false);
const activeMessage = ref<OutboundMessage | null>(null);
const selectedTemplateId = ref("");
const recipientIdentifierType = ref("phone");
const recipientAddress = ref("");
const recipientSnapshotText = ref(formatJsonObject({}));
const variablesText = ref(formatJsonObject({}));
const priority = ref(100);

const outboundQueryParams = computed(() => ({
  limit: PAGE_SIZE,
  offset: offset.value,
}));
const messagesQuery = useOutboundMessagesQuery(outboundQueryParams);
const templatesQuery = useMessageTemplatesQuery();
const sendMutation = useSendCommunicationMutation();

const messages = computed(() => messagesQuery.data.value?.items ?? []);
const activeTemplates = computed(() =>
  (templatesQuery.data.value?.items ?? []).filter(
    (template) =>
      template.status === "ACTIVE" &&
      template.active_version_id &&
      !template.status.startsWith("ARCHIV"),
  ),
);
const selectedTemplate = computed(() =>
  activeTemplates.value.find(
    (template) => template.template_id === selectedTemplateId.value,
  ),
);
const searchQuery = computed(() => {
  const value = route.query.q;
  return typeof value === "string" ? value : "";
});
const isSendTestSheetOpen = computed({
  get: () => route.query.send === "test",
  set: (value: boolean) => {
    patchQuery({ send: value ? "test" : undefined });
  },
});
const currentPage = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1);
const canGoPrevious = computed(() => offset.value > 0);
const canGoNext = computed(() => messages.value.length === PAGE_SIZE);
const columns: ColumnDef<OutboundMessage>[] = [
  {
    id: "status",
    accessorKey: "internal_status",
    header: "Status",
  },
  {
    id: "channel_code",
    accessorKey: "channel_code",
    header: "Channel",
  },
  {
    id: "recipient",
    accessorFn: (message) =>
      `${message.recipient_address} ${message.recipient_identifier_type}`,
    header: "Recipient",
  },
  {
    id: "provider_status",
    accessorKey: "external_status",
    header: "Provider status",
  },
  {
    id: "external_message_id",
    accessorKey: "external_message_id",
    header: "External ID",
  },
  {
    id: "queued_at",
    accessorKey: "queued_at",
    header: "Queued",
  },
  {
    id: "sent_at",
    accessorKey: "sent_at",
    header: "Sent",
  },
  {
    id: "delivered_at",
    accessorKey: "delivered_at",
    header: "Delivered",
  },
  {
    id: "failed_at",
    accessorKey: "failed_at",
    header: "Failed",
  },
  {
    id: "updated_at",
    accessorKey: "updated_at",
    header: "Updated",
  },
  {
    id: "details",
    header: "Details",
    enableGlobalFilter: false,
  },
];
const table = useVueTable({
  data: messages,
  columns,
  getCoreRowModel: getCoreRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  state: {
    get globalFilter() {
      return searchQuery.value;
    },
  },
});
const visibleRows = computed(() => table.getRowModel().rows);
const columnCount = computed(() => table.getVisibleLeafColumns().length);

watch(
  activeTemplates,
  (items) => {
    if (!items.length) {
      selectedTemplateId.value = "";
      return;
    }

    if (
      !selectedTemplateId.value ||
      !items.some((item) => item.template_id === selectedTemplateId.value)
    ) {
      selectedTemplateId.value = items[0].template_id;
    }
  },
  { immediate: true },
);

watch(selectedTemplate, (template) => {
  if (!template) {
    return;
  }

  recipientIdentifierType.value =
    template.channel_code === "EMAIL" ? "email" : "phone";
});

function patchQuery(patch: Record<string, string | undefined>) {
  const nextQuery = { ...route.query };

  for (const [key, value] of Object.entries(patch)) {
    if (!value) {
      delete nextQuery[key];
    } else {
      nextQuery[key] = value;
    }
  }

  router.replace({ query: nextQuery });
}

async function refreshDeliveries() {
  await Promise.all([messagesQuery.refetch(), templatesQuery.refetch()]);
}

async function sendTestMessage() {
  const template = selectedTemplate.value;

  if (!template) {
    toast.error("Select an active template.");
    return;
  }

  try {
    const recipientSnapshot = parseJsonObject(recipientSnapshotText.value, {});
    const variables = parseJsonObject(variablesText.value, {});
    const result = await sendMutation.mutateAsync({
      initiator_type: "CONSOLE_TEST",
      initiator_ref_id: "communication-deliveries",
      correlation_id: createClientUuid(),
      idempotency_key: createClientUuid(),
      channel_code: template.channel_code,
      template_id: template.template_id,
      recipient_identifier_type: recipientIdentifierType.value.trim(),
      recipient_address: recipientAddress.value.trim(),
      recipient_snapshot: recipientSnapshot,
      message_class: template.message_class,
      variables,
      scheduled_at: null,
      priority: Number(priority.value),
    });

    toast.success(`Test message queued: ${result.internal_status}.`);
    isSendTestSheetOpen.value = false;
    offset.value = 0;
    await messagesQuery.refetch();
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

function goPrevious() {
  offset.value = Math.max(0, offset.value - PAGE_SIZE);
}

function goNext() {
  offset.value += PAGE_SIZE;
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

function prettyJson(value: JsonObject) {
  return JSON.stringify(value, null, 2);
}

function templateLabel(template: MessageTemplate) {
  return `${template.name} · ${template.channel_code}`;
}
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between"
    >
      <CommunicationPageHeader
        title="Deliveries"
        description="Search, inspect, and page through outbound communication messages and provider statuses."
      />
      <Button
        type="button"
        variant="outline"
        :disabled="
          messagesQuery.isFetching.value || templatesQuery.isFetching.value
        "
        @click="refreshDeliveries"
      >
        <RefreshCcw
          class="size-4"
          :class="{
            'animate-spin':
              messagesQuery.isFetching.value || templatesQuery.isFetching.value,
          }"
        />
        Refresh
      </Button>
    </div>

    <Alert
      v-if="messagesQuery.error.value || templatesQuery.error.value"
      variant="destructive"
    >
      <AlertDescription>
        {{
          apiErrorMessage(
            messagesQuery.error.value ?? templatesQuery.error.value,
          )
        }}
      </AlertDescription>
    </Alert>

    <DeliveriesToolBar />

    <div
      class="min-h-0 flex-1 overflow-hidden rounded-lg border [&>[data-slot=table-container]]:h-full"
    >
      <Table>
        <TableHeader class="sticky top-0 z-20 bg-background">
          <TableRow>
            <TableHead
              v-for="header in table.getHeaderGroups()[0]?.headers ?? []"
              :key="header.id"
              :class="{
                'w-32': ['status', 'channel_code'].includes(header.column.id),
                'w-44': ['provider_status', 'external_message_id'].includes(
                  header.column.id,
                ),
                'w-40': [
                  'queued_at',
                  'sent_at',
                  'delivered_at',
                  'failed_at',
                  'updated_at',
                ].includes(header.column.id),
                'w-20 text-right': header.column.id === 'details',
              }"
            >
              {{ header.column.columnDef.header }}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="messagesQuery.isLoading.value">
            <TableRow v-for="index in 8" :key="index">
              <TableCell>
                <Skeleton class="h-5 w-20" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-16" />
              </TableCell>
              <TableCell>
                <div class="grid gap-2">
                  <Skeleton class="h-4 w-40" />
                  <Skeleton class="h-3 w-24" />
                </div>
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-24" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-36" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="ml-auto h-8 w-8" />
              </TableCell>
            </TableRow>
          </template>

          <TableEmpty
            v-else-if="visibleRows.length === 0"
            :colspan="columnCount"
            class="text-muted-foreground"
          >
            No deliveries found.
          </TableEmpty>

          <TableRow
            v-for="row in visibleRows"
            v-else
            :key="row.id"
            class="cursor-pointer animate-in fade-in-0 slide-in-from-top-1 duration-300"
            @click="openDetails(row.original)"
          >
            <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id">
              <StatusBadge
                v-if="cell.column.id === 'status'"
                :status="row.original.internal_status"
              />

              <Badge
                v-else-if="cell.column.id === 'channel_code'"
                variant="secondary"
              >
                {{ row.original.channel_code }}
              </Badge>

              <div
                v-else-if="cell.column.id === 'recipient'"
                class="grid gap-1"
              >
                <span class="text-sm font-medium">
                  {{ row.original.recipient_address }}
                </span>
                <span class="text-xs text-muted-foreground">
                  {{ row.original.recipient_identifier_type }}
                </span>
              </div>

              <span
                v-else-if="cell.column.id === 'provider_status'"
                class="text-sm"
              >
                {{ row.original.external_status ?? "-" }}
              </span>

              <span
                v-else-if="cell.column.id === 'external_message_id'"
                class="font-mono text-xs"
              >
                {{ row.original.external_message_id ?? "-" }}
              </span>

              <span
                v-else-if="cell.column.id !== 'details'"
                class="whitespace-nowrap text-sm text-muted-foreground"
              >
                {{
                  formatDate(
                    row.original[cell.column.id as keyof OutboundMessage] as
                      | string
                      | null,
                  )
                }}
              </span>

              <div v-else class="flex justify-end">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  @click.stop="openDetails(row.original)"
                >
                  <Eye class="size-4" />
                  <span class="sr-only">
                    Open {{ shortId(row.original.outbound_message_id) }}
                  </span>
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-center md:justify-between"
    >
      <p class="text-sm text-muted-foreground">
        Page {{ currentPage }} · showing {{ visibleRows.length }} of
        {{ PAGE_SIZE }} loaded
      </p>
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

    <Sheet v-model:open="isSendTestSheetOpen">
      <SheetContent
        class="w-[min(34rem,100vw)] gap-2 overflow-y-auto p-4 sm:max-w-xl"
      >
        <SheetHeader class="gap-1 p-0 pr-8">
          <SheetTitle>Send test</SheetTitle>
          <SheetDescription>
            Queue one message with recipient data and template variables.
          </SheetDescription>
        </SheetHeader>

        <form class="grid gap-2" @submit.prevent="sendTestMessage">
          <div class="grid gap-2">
            <label class="text-sm font-medium" for="test-template">
              Template
            </label>
            <select
              id="test-template"
              v-model="selectedTemplateId"
              required
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="template in activeTemplates"
                :key="template.template_id"
                :value="template.template_id"
              >
                {{ templateLabel(template) }}
              </option>
            </select>
            <span
              v-if="!activeTemplates.length"
              class="text-xs text-muted-foreground"
            >
              No active templates available.
            </span>
          </div>

          <div class="grid gap-2 md:grid-cols-2">
            <div class="grid gap-2">
              <label class="text-sm font-medium" for="recipient-type">
                Recipient type
              </label>
              <Input
                id="recipient-type"
                v-model="recipientIdentifierType"
                required
              />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium" for="recipient-address">
                Recipient address
              </label>
              <Input
                id="recipient-address"
                v-model="recipientAddress"
                required
              />
            </div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="variables">Variables</label>
            <Textarea
              id="variables"
              v-model="variablesText"
              class="min-h-28 font-mono text-xs"
            />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="recipient-snapshot">
              Recipient snapshot
            </label>
            <Textarea
              id="recipient-snapshot"
              v-model="recipientSnapshotText"
              class="min-h-24 font-mono text-xs"
            />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="priority">Priority</label>
            <Input
              id="priority"
              v-model.number="priority"
              min="0"
              required
              type="number"
            />
          </div>

          <SheetFooter class="mt-2 gap-2 p-0 sm:flex-row sm:justify-end">
            <Button
              type="submit"
              :disabled="!selectedTemplate || sendMutation.isPending.value"
            >
              <SendHorizontal class="size-4" />
              {{ sendMutation.isPending.value ? "Sending" : "Send" }}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>

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
              <span class="text-sm font-medium">
                {{ activeMessage.channel_code }}
              </span>
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
