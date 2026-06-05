<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  getCoreRowModel,
  getFilteredRowModel,
  useVueTable,
  type ColumnDef,
} from "@tanstack/vue-table";
import { RefreshCcw, Save } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  ProviderConnection,
  ProviderConnector,
  ProviderMessageType,
} from "@/modules/communication/api";
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";
import JsonSchemaForm from "@/modules/communication/components/JsonSchemaForm.vue";
import StatusBadge from "@/modules/communication/components/StatusBadge.vue";
import TemplatesToolBar from "@/modules/communication/components/TemplatesToolBar.vue";
import {
  apiErrorMessage,
  buildJsonSchemaDefaults,
  formatJsonObject,
  parseJsonObject,
} from "@/modules/communication/lib";
import { useCreateMessageTemplateWithVersionMutation } from "@/modules/communication/mutations/use-create-message-template-with-version";
import { useProviderCatalogQuery } from "@/modules/communication/queries/use-provider-catalog-query";
import { useProviderConnectionsQuery } from "@/modules/communication/queries/use-provider-connections-query";
import { useMessageTemplatesQuery } from "@/modules/communication/queries/use-message-templates-query";

const MESSAGE_CLASSES = [
  "TRANSACTIONAL",
  "MARKETING",
  "SERVICE",
  "OTP",
  "INFO",
];

const route = useRoute();
const router = useRouter();

const selectedConnectionId = ref("");
const selectedMessageTypeId = ref("");
const templateCode = ref("");
const templateName = ref("");
const templateDescription = ref("");
const messageClass = ref("TRANSACTIONAL");
const templatePayload = ref<JsonObject>({});
const variablesSchemaText = ref(
  formatJsonObject({
    type: "object",
    properties: {},
  }),
);

const catalogQuery = useProviderCatalogQuery();
const connectionsQuery = useProviderConnectionsQuery();
const templatesQuery = useMessageTemplatesQuery();
const createTemplateMutation = useCreateMessageTemplateWithVersionMutation();

const connectors = computed(() =>
  (catalogQuery.data.value?.connectors ?? []).filter(
    (connector) => !connector.status.startsWith("ARCHIV"),
  ),
);
const connectorById = computed(() =>
  connectors.value.reduce<Record<string, ProviderConnector>>(
    (index, connector) => {
      index[connector.provider_connector_id] = connector;
      return index;
    },
    {},
  ),
);
const messageTypes = computed(
  () => catalogQuery.data.value?.message_types ?? [],
);
const messageTypeById = computed(() =>
  messageTypes.value.reduce<Record<string, ProviderMessageType>>(
    (index, messageType) => {
      index[messageType.provider_message_type_id] = messageType;
      return index;
    },
    {},
  ),
);
const connections = computed(() =>
  (connectionsQuery.data.value?.items ?? []).filter(
    (connection) => !connection.status.startsWith("ARCHIV"),
  ),
);
const activeConnections = computed(() =>
  connections.value.filter((connection) => {
    const connector = connectorById.value[connection.provider_connector_id];
    return connection.status === "ACTIVE" && connector?.status === "ACTIVE";
  }),
);
const selectedConnection = computed(() =>
  activeConnections.value.find(
    (connection) =>
      connection.provider_connection_id === selectedConnectionId.value,
  ),
);
const selectedConnector = computed(() =>
  selectedConnection.value
    ? connectorById.value[selectedConnection.value.provider_connector_id]
    : undefined,
);
const availableMessageTypes = computed(() =>
  messageTypes.value.filter(
    (messageType) =>
      messageType.provider_connector_id ===
        selectedConnection.value?.provider_connector_id &&
      messageType.channel_code === selectedConnection.value?.channel_code &&
      messageType.is_active,
  ),
);
const selectedMessageType = computed(() =>
  availableMessageTypes.value.find(
    (messageType) =>
      messageType.provider_message_type_id === selectedMessageTypeId.value,
  ),
);
const templates = computed(() =>
  (templatesQuery.data.value?.items ?? []).filter(
    (template) => !template.status.startsWith("ARCHIV"),
  ),
);
const searchQuery = computed(() => {
  const value = route.query.q;
  return typeof value === "string" ? value : "";
});
const isCreateSheetOpen = computed({
  get: () => route.query.create === "template",
  set: (value: boolean) => {
    patchQuery({ create: value ? "template" : undefined });
  },
});
const isLoading = computed(
  () =>
    catalogQuery.isLoading.value ||
    connectionsQuery.isLoading.value ||
    templatesQuery.isLoading.value,
);
const isFetching = computed(
  () =>
    catalogQuery.isFetching.value ||
    connectionsQuery.isFetching.value ||
    templatesQuery.isFetching.value,
);
const columns: ColumnDef<MessageTemplate>[] = [
  {
    id: "template",
    accessorFn: (template) =>
      `${template.name} ${template.template_code} ${template.description ?? ""}`,
    header: "Template",
  },
  {
    id: "provider",
    accessorFn: (template) =>
      `${connectorName(template.provider_connector_id)} ${messageTypeName(template.provider_message_type_id)}`,
    header: "Provider",
  },
  {
    id: "channel_code",
    accessorKey: "channel_code",
    header: "Channel",
  },
  {
    id: "message_class",
    accessorKey: "message_class",
    header: "Class",
  },
  {
    id: "status",
    accessorKey: "status",
    header: "Status",
  },
  {
    id: "active_version",
    accessorKey: "active_version",
    header: "Active version",
  },
  {
    id: "updated_at",
    accessorKey: "updated_at",
    header: "Updated",
  },
];
const table = useVueTable({
  data: templates,
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
  activeConnections,
  (items) => {
    if (!items.length) {
      selectedConnectionId.value = "";
      return;
    }

    if (
      !selectedConnectionId.value ||
      !items.some(
        (item) => item.provider_connection_id === selectedConnectionId.value,
      )
    ) {
      selectedConnectionId.value = items[0].provider_connection_id;
    }
  },
  { immediate: true },
);

watch(
  availableMessageTypes,
  (items) => {
    if (!items.length) {
      selectedMessageTypeId.value = "";
      templatePayload.value = {};
      return;
    }

    if (
      !selectedMessageTypeId.value ||
      !items.some(
        (item) => item.provider_message_type_id === selectedMessageTypeId.value,
      )
    ) {
      selectedMessageTypeId.value = items[0].provider_message_type_id;
    }
  },
  { immediate: true },
);

watch(selectedMessageType, (messageType) => {
  if (!messageType) {
    return;
  }

  templateCode.value = `${messageType.message_type_code}_template`;
  templateName.value = messageType.name;
  templatePayload.value = buildJsonSchemaDefaults(messageType.field_schema);
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

async function refreshTemplates() {
  await Promise.all([
    catalogQuery.refetch(),
    connectionsQuery.refetch(),
    templatesQuery.refetch(),
  ]);
}

async function createTemplateWithActiveVersion() {
  const connection = selectedConnection.value;
  const messageType = selectedMessageType.value;

  if (!connection || !messageType) {
    toast.error("Select an active connection and message type.");
    return;
  }

  try {
    const variablesSchema = parseJsonObject(variablesSchemaText.value, {
      type: "object",
      properties: {},
    });
    const template = await createTemplateMutation.mutateAsync({
      template: {
        template_code: templateCode.value.trim(),
        name: templateName.value.trim(),
        description: templateDescription.value.trim() || null,
        provider_connector_id: connection.provider_connector_id,
        provider_message_type_id: messageType.provider_message_type_id,
        channel_code: connection.channel_code,
        message_class: messageClass.value,
      },
      version: {
        template_payload: templatePayload.value,
        variables_schema: variablesSchema,
      },
    });

    toast.success(`${template.name} created.`);
    isCreateSheetOpen.value = false;
    await templatesQuery.refetch();
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

function connectorName(connectorId: string) {
  return connectorById.value[connectorId]?.provider_name ?? connectorId;
}

function connectionLabel(connection: ProviderConnection) {
  const connector = connectorById.value[connection.provider_connector_id];
  return `${connection.connection_name} · ${connector?.provider_name ?? connection.channel_code}`;
}

function providerCode(connectorId: string) {
  return connectorById.value[connectorId]?.provider_code ?? connectorId;
}

function messageTypeName(messageTypeId: string) {
  return messageTypeById.value[messageTypeId]?.name ?? messageTypeId;
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
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between"
    >
      <CommunicationPageHeader
        title="Templates"
        description="Create provider-bound message templates and inspect active payload versions."
      />
      <Button
        type="button"
        variant="outline"
        :disabled="isFetching"
        @click="refreshTemplates"
      >
        <RefreshCcw class="size-4" :class="{ 'animate-spin': isFetching }" />
        Refresh
      </Button>
    </div>

    <Alert
      v-if="
        catalogQuery.error.value ||
        connectionsQuery.error.value ||
        templatesQuery.error.value
      "
      variant="destructive"
    >
      <AlertDescription>
        {{
          apiErrorMessage(
            catalogQuery.error.value ??
              connectionsQuery.error.value ??
              templatesQuery.error.value,
          )
        }}
      </AlertDescription>
    </Alert>

    <TemplatesToolBar />

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
                'w-36': ['channel_code', 'message_class'].includes(
                  header.column.id,
                ),
                'w-40': header.column.id === 'status',
                'w-48': ['active_version', 'updated_at'].includes(
                  header.column.id,
                ),
              }"
            >
              {{ header.column.columnDef.header }}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="isLoading">
            <TableRow v-for="index in 8" :key="index">
              <TableCell>
                <div class="grid gap-2">
                  <Skeleton class="h-4 w-40" />
                  <Skeleton class="h-3 w-28" />
                </div>
              </TableCell>
              <TableCell>
                <div class="grid gap-2">
                  <Skeleton class="h-4 w-32" />
                  <Skeleton class="h-3 w-24" />
                </div>
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-16" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-28" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-20" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
            </TableRow>
          </template>

          <TableEmpty
            v-else-if="visibleRows.length === 0"
            :colspan="columnCount"
            class="text-muted-foreground"
          >
            No templates found.
          </TableEmpty>

          <TableRow
            v-for="row in visibleRows"
            v-else
            :key="row.id"
            class="animate-in fade-in-0 slide-in-from-top-1 duration-300"
          >
            <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id">
              <div v-if="cell.column.id === 'template'" class="grid gap-1">
                <span class="font-medium">
                  {{ row.original.name }}
                </span>
                <span class="font-mono text-xs text-muted-foreground">
                  {{ row.original.template_code }}
                </span>
                <span
                  v-if="row.original.description"
                  class="line-clamp-2 max-w-xl text-xs text-muted-foreground"
                >
                  {{ row.original.description }}
                </span>
              </div>

              <div v-else-if="cell.column.id === 'provider'" class="grid gap-1">
                <span class="text-sm font-medium">
                  {{ connectorName(row.original.provider_connector_id) }}
                </span>
                <span class="text-xs text-muted-foreground">
                  {{ providerCode(row.original.provider_connector_id) }} ·
                  {{ messageTypeName(row.original.provider_message_type_id) }}
                </span>
              </div>

              <Badge
                v-else-if="cell.column.id === 'channel_code'"
                variant="secondary"
              >
                {{ row.original.channel_code }}
              </Badge>

              <Badge
                v-else-if="cell.column.id === 'message_class'"
                variant="outline"
              >
                {{ row.original.message_class }}
              </Badge>

              <StatusBadge
                v-else-if="cell.column.id === 'status'"
                :status="row.original.status"
              />

              <span
                v-else-if="cell.column.id === 'active_version'"
                class="whitespace-nowrap text-sm text-muted-foreground"
              >
                {{ formatDate(row.original.active_version) }}
              </span>

              <span
                v-else
                class="whitespace-nowrap text-sm text-muted-foreground"
              >
                {{ formatDate(row.original.updated_at) }}
              </span>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <Sheet v-model:open="isCreateSheetOpen">
      <SheetContent
        class="w-[min(34rem,100vw)] gap-2 overflow-y-auto p-4 sm:max-w-xl"
      >
        <SheetHeader class="gap-1 p-0 pr-8">
          <SheetTitle>Create template</SheetTitle>
          <SheetDescription>
            Select an active connection and fill the provider payload.
          </SheetDescription>
        </SheetHeader>

        <form
          class="grid gap-2"
          @submit.prevent="createTemplateWithActiveVersion"
        >
          <div class="grid gap-2">
            <label class="text-sm font-medium" for="template-connection">
              Connection
            </label>
            <select
              id="template-connection"
              v-model="selectedConnectionId"
              required
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="connection in activeConnections"
                :key="connection.provider_connection_id"
                :value="connection.provider_connection_id"
              >
                {{ connectionLabel(connection) }} ·
                {{ connection.channel_code }}
              </option>
            </select>
            <span
              v-if="!activeConnections.length"
              class="text-xs text-muted-foreground"
            >
              No active provider connections available.
            </span>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="template-message-type">
              Message type
            </label>
            <select
              id="template-message-type"
              v-model="selectedMessageTypeId"
              required
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="messageType in availableMessageTypes"
                :key="messageType.provider_message_type_id"
                :value="messageType.provider_message_type_id"
              >
                {{ messageType.name }} · {{ messageType.message_type_code }}
              </option>
            </select>
            <span
              v-if="selectedConnector"
              class="text-xs text-muted-foreground"
            >
              {{ selectedConnector.provider_name }}
            </span>
          </div>

          <div class="grid gap-2 md:grid-cols-2">
            <div class="grid gap-2">
              <label class="text-sm font-medium" for="template-code">
                Code
              </label>
              <Input id="template-code" v-model="templateCode" required />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium" for="template-name">
                Name
              </label>
              <Input id="template-name" v-model="templateName" required />
            </div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="template-message-class">
              Message class
            </label>
            <select
              id="template-message-class"
              v-model="messageClass"
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option v-for="item in MESSAGE_CLASSES" :key="item" :value="item">
                {{ item }}
              </option>
            </select>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="template-description">
              Description
            </label>
            <Textarea
              id="template-description"
              v-model="templateDescription"
              class="min-h-16"
            />
          </div>

          <div class="grid gap-2">
            <h3 class="text-sm font-medium">Payload</h3>
            <JsonSchemaForm
              v-model="templatePayload"
              :schema="selectedMessageType?.field_schema"
              :ui-schema="selectedMessageType?.ui_schema"
            />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="variables-schema">
              Variables schema
            </label>
            <Textarea
              id="variables-schema"
              v-model="variablesSchemaText"
              class="min-h-28 font-mono text-xs"
            />
          </div>

          <SheetFooter class="mt-2 gap-2 p-0 sm:flex-row sm:justify-end">
            <Button
              type="submit"
              :disabled="
                !selectedConnection ||
                !selectedMessageType ||
                createTemplateMutation.isPending.value
              "
            >
              <Save class="size-4" />
              {{
                createTemplateMutation.isPending.value ? "Creating" : "Create"
              }}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  </section>
</template>
