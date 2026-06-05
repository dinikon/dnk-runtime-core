<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  getCoreRowModel,
  getFilteredRowModel,
  useVueTable,
  type ColumnDef,
} from "@tanstack/vue-table";
import {
  CheckCircle2,
  PauseCircle,
  PlugZap,
  RefreshCcw,
  Trash2,
} from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import type {
  JsonObject,
  ProviderConnection,
  ProviderConnectionMutableStatus,
  ProviderConnector,
} from "@/modules/communication/api";
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";
import ConnectionsToolBar from "@/modules/communication/components/ConnectionsToolBar.vue";
import JsonSchemaForm from "@/modules/communication/components/JsonSchemaForm.vue";
import StatusBadge from "@/modules/communication/components/StatusBadge.vue";
import {
  apiErrorMessage,
  buildJsonSchemaDefaults,
  compactJsonObject,
} from "@/modules/communication/lib";
import { useCreateProviderConnectionMutation } from "@/modules/communication/mutations/use-create-provider-connection";
import { useDeleteProviderConnectionMutation } from "@/modules/communication/mutations/use-delete-provider-connection";
import { useUpdateProviderConnectionStatusMutation } from "@/modules/communication/mutations/use-update-provider-connection-status";
import { useProviderCatalogQuery } from "@/modules/communication/queries/use-provider-catalog-query";
import { useProviderConnectionsQuery } from "@/modules/communication/queries/use-provider-connections-query";

const route = useRoute();
const router = useRouter();

const selectedConnectorId = ref("");
const connectionCode = ref("");
const connectionName = ref("");
const channelCode = ref("");
const secretRef = ref("");
const configValues = ref<JsonObject>({});
const secretValues = ref<JsonObject>({});
const pendingConnectionId = ref<string | null>(null);
const connectionPendingDeletion = ref<ProviderConnection | null>(null);

const catalogQuery = useProviderCatalogQuery();
const connectionsQuery = useProviderConnectionsQuery();
const createConnectionMutation = useCreateProviderConnectionMutation();
const updateStatusMutation = useUpdateProviderConnectionStatusMutation();
const deleteMutation = useDeleteProviderConnectionMutation();

const connectors = computed(() =>
  (catalogQuery.data.value?.connectors ?? []).filter(
    (connector) => !connector.status.startsWith("ARCHIV"),
  ),
);
const activeConnectors = computed(() =>
  connectors.value.filter((connector) => connector.status === "ACTIVE"),
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
const connections = computed(() =>
  (connectionsQuery.data.value?.items ?? []).filter(
    (connection) => !connection.status.startsWith("ARCHIV"),
  ),
);
const selectedConnector = computed(() =>
  activeConnectors.value.find(
    (connector) =>
      connector.provider_connector_id === selectedConnectorId.value,
  ),
);
const searchQuery = computed(() => {
  const value = route.query.q;
  return typeof value === "string" ? value : "";
});
const isCreateSheetOpen = computed({
  get: () => route.query.create === "connection",
  set: (value: boolean) => {
    patchQuery({ create: value ? "connection" : undefined });
  },
});
const actionPending = computed(
  () => updateStatusMutation.isPending.value || deleteMutation.isPending.value,
);
const columns: ColumnDef<ProviderConnection>[] = [
  {
    id: "connection",
    accessorFn: (connection) =>
      `${connection.connection_name} ${connection.connection_code}`,
    header: "Connection",
  },
  {
    id: "provider",
    accessorFn: (connection) => providerName(connection),
    header: "Provider",
  },
  {
    id: "channel_code",
    accessorKey: "channel_code",
    header: "Channel",
  },
  {
    id: "config",
    accessorFn: (connection) => JSON.stringify(connection.config),
    header: "Config",
  },
  {
    id: "secrets",
    accessorFn: (connection) =>
      [connection.has_secrets ? "secrets" : "", connection.secret_ref ?? ""]
        .filter(Boolean)
        .join(" "),
    header: "Secrets",
  },
  {
    id: "status",
    accessorKey: "status",
    header: "Status",
  },
  {
    id: "updated_at",
    accessorKey: "updated_at",
    header: "Updated",
  },
  {
    id: "actions",
    header: "Actions",
    enableGlobalFilter: false,
  },
];
const table = useVueTable({
  data: connections,
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
  activeConnectors,
  (items) => {
    if (!items.length) {
      selectedConnectorId.value = "";
      resetConnectionForm();
      return;
    }

    if (
      !selectedConnectorId.value ||
      !items.some(
        (item) => item.provider_connector_id === selectedConnectorId.value,
      )
    ) {
      selectedConnectorId.value = items[0].provider_connector_id;
    }
  },
  { immediate: true },
);

watch(selectedConnector, (connector) => {
  if (!connector) {
    resetConnectionForm();
    return;
  }

  connectionCode.value = `${connector.provider_code}_main`;
  connectionName.value = `${connector.provider_name} main`;
  channelCode.value = connector.channels[0] ?? "";
  configValues.value = buildJsonSchemaDefaults(connector.config_schema);
  secretValues.value = buildJsonSchemaDefaults(connector.secrets_schema);
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

async function refreshConnections() {
  await Promise.all([connectionsQuery.refetch(), catalogQuery.refetch()]);
}

async function createConnection() {
  const connector = selectedConnector.value;

  if (!connector) {
    toast.error("Select an active provider.");
    return;
  }

  try {
    const connection = await createConnectionMutation.mutateAsync({
      provider_connector_id: connector.provider_connector_id,
      connection_code: connectionCode.value.trim(),
      connection_name: connectionName.value.trim(),
      channel_code: channelCode.value,
      config: compactJsonObject(configValues.value),
      secrets: compactJsonObject(secretValues.value),
      secret_ref: secretRef.value.trim() || null,
    });
    toast.success(`${connection.connection_name} created.`);
    isCreateSheetOpen.value = false;
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

async function updateConnectionStatus(
  connection: ProviderConnection,
  status: ProviderConnectionMutableStatus,
) {
  pendingConnectionId.value = connection.provider_connection_id;

  try {
    const updatedConnection = await updateStatusMutation.mutateAsync({
      provider_connection_id: connection.provider_connection_id,
      status,
    });
    toast.success(
      `${updatedConnection.connection_name} is ${status.toLowerCase()}.`,
    );
  } catch (error) {
    toast.error(apiErrorMessage(error));
  } finally {
    pendingConnectionId.value = null;
  }
}

async function deleteConnection() {
  const connection = connectionPendingDeletion.value;

  if (!connection) {
    return;
  }

  pendingConnectionId.value = connection.provider_connection_id;

  try {
    await deleteMutation.mutateAsync(connection.provider_connection_id);
    toast.success(`${connection.connection_name} deleted.`);
    connectionPendingDeletion.value = null;
  } catch (error) {
    toast.error(apiErrorMessage(error));
  } finally {
    pendingConnectionId.value = null;
  }
}

function resetConnectionForm() {
  connectionCode.value = "";
  connectionName.value = "";
  channelCode.value = "";
  secretRef.value = "";
  configValues.value = {};
  secretValues.value = {};
}

function providerName(connection: ProviderConnection) {
  const connector = connectorById.value[connection.provider_connector_id];
  return connector?.provider_name ?? connection.provider_connector_id;
}

function providerCode(connection: ProviderConnection) {
  const connector = connectorById.value[connection.provider_connector_id];
  return connector?.provider_code ?? connection.provider_connector_id;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function isConnectionPending(connection: ProviderConnection) {
  return (
    pendingConnectionId.value === connection.provider_connection_id &&
    actionPending.value
  );
}
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between"
    >
      <CommunicationPageHeader
        title="Connections"
        description="Create provider connections, review tenant-specific credentials and manage lifecycle status."
      />
      <Button
        type="button"
        variant="outline"
        :disabled="
          connectionsQuery.isFetching.value || catalogQuery.isFetching.value
        "
        @click="refreshConnections"
      >
        <RefreshCcw
          class="size-4"
          :class="{
            'animate-spin':
              connectionsQuery.isFetching.value ||
              catalogQuery.isFetching.value,
          }"
        />
        Refresh
      </Button>
    </div>

    <Alert
      v-if="connectionsQuery.error.value || catalogQuery.error.value"
      variant="destructive"
    >
      <AlertDescription>
        {{
          apiErrorMessage(
            connectionsQuery.error.value ?? catalogQuery.error.value,
          )
        }}
      </AlertDescription>
    </Alert>

    <ConnectionsToolBar />

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
                'sticky right-0 z-10 w-56 bg-background text-right':
                  header.column.id === 'actions',
                'w-36': header.column.id === 'channel_code',
                'w-40': header.column.id === 'status',
                'w-48': header.column.id === 'updated_at',
              }"
            >
              {{ header.column.columnDef.header }}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="connectionsQuery.isLoading.value">
            <TableRow v-for="index in 8" :key="index">
              <TableCell>
                <div class="grid gap-2">
                  <Skeleton class="h-4 w-40" />
                  <Skeleton class="h-3 w-28" />
                </div>
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-16" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-20" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-24" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-20" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-32" />
              </TableCell>
              <TableCell>
                <Skeleton class="ml-auto h-8 w-36" />
              </TableCell>
            </TableRow>
          </template>

          <TableEmpty
            v-else-if="visibleRows.length === 0"
            :colspan="columnCount"
            class="text-muted-foreground"
          >
            No connections found.
          </TableEmpty>

          <TableRow
            v-for="row in visibleRows"
            v-else
            :key="row.id"
            class="animate-in fade-in-0 slide-in-from-top-1 duration-300"
          >
            <TableCell
              v-for="cell in row.getVisibleCells()"
              :key="cell.id"
              :class="{
                'sticky right-0 bg-background': cell.column.id === 'actions',
              }"
            >
              <div v-if="cell.column.id === 'connection'" class="grid gap-1">
                <span class="font-medium">
                  {{ row.original.connection_name }}
                </span>
                <span class="font-mono text-xs text-muted-foreground">
                  {{ row.original.connection_code }}
                </span>
              </div>

              <div v-else-if="cell.column.id === 'provider'" class="grid gap-1">
                <span class="text-sm font-medium">
                  {{ providerName(row.original) }}
                </span>
                <span class="text-xs text-muted-foreground">
                  {{ providerCode(row.original) }}
                </span>
              </div>

              <Badge
                v-else-if="cell.column.id === 'channel_code'"
                variant="secondary"
              >
                {{ row.original.channel_code }}
              </Badge>

              <span
                v-else-if="cell.column.id === 'config'"
                class="text-sm text-muted-foreground"
              >
                {{ Object.keys(row.original.config).length }} keys
              </span>

              <div v-else-if="cell.column.id === 'secrets'" class="flex gap-1">
                <Badge v-if="row.original.has_secrets" variant="outline">
                  Secrets
                </Badge>
                <Badge v-if="row.original.secret_ref" variant="outline">
                  {{ row.original.secret_ref }}
                </Badge>
                <span
                  v-if="!row.original.has_secrets && !row.original.secret_ref"
                  class="text-sm text-muted-foreground"
                >
                  -
                </span>
              </div>

              <StatusBadge
                v-else-if="cell.column.id === 'status'"
                :status="row.original.status"
              />

              <span
                v-else-if="cell.column.id === 'updated_at'"
                class="whitespace-nowrap text-sm text-muted-foreground"
              >
                {{ formatDate(row.original.updated_at) }}
              </span>

              <div v-else class="flex justify-end gap-2">
                <Button
                  v-if="row.original.status === 'ACTIVE'"
                  type="button"
                  variant="outline"
                  size="sm"
                  :disabled="isConnectionPending(row.original)"
                  @click="updateConnectionStatus(row.original, 'DISABLED')"
                >
                  <PauseCircle class="size-4" />
                  Deactivate
                </Button>
                <Button
                  v-if="row.original.status === 'DISABLED'"
                  type="button"
                  variant="outline"
                  size="sm"
                  :disabled="isConnectionPending(row.original)"
                  @click="updateConnectionStatus(row.original, 'ACTIVE')"
                >
                  <CheckCircle2 class="size-4" />
                  Activate
                </Button>
                <Button
                  v-if="row.original.status === 'DISABLED'"
                  type="button"
                  variant="ghost"
                  size="sm"
                  class="text-destructive hover:text-destructive"
                  :disabled="isConnectionPending(row.original)"
                  @click="connectionPendingDeletion = row.original"
                >
                  <Trash2 class="size-4" />
                  Delete
                </Button>
              </div>
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
          <SheetTitle>Create connection</SheetTitle>
          <SheetDescription>
            Select an active provider and fill connection config.
          </SheetDescription>
        </SheetHeader>

        <form class="grid gap-2" @submit.prevent="createConnection">
          <div class="grid gap-2">
            <label class="text-sm font-medium" for="provider-connector">
              Provider
            </label>
            <select
              id="provider-connector"
              v-model="selectedConnectorId"
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="connector in activeConnectors"
                :key="connector.provider_connector_id"
                :value="connector.provider_connector_id"
              >
                {{ connector.provider_name }} ({{ connector.provider_code }})
              </option>
            </select>
          </div>

          <div class="grid gap-2 md:grid-cols-2">
            <div class="grid gap-2">
              <label class="text-sm font-medium" for="connection-code">
                Code
              </label>
              <Input id="connection-code" v-model="connectionCode" required />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium" for="connection-name">
                Name
              </label>
              <Input id="connection-name" v-model="connectionName" required />
            </div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="connection-channel">
              Channel
            </label>
            <select
              id="connection-channel"
              v-model="channelCode"
              required
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="channel in selectedConnector?.channels ?? []"
                :key="channel"
                :value="channel"
              >
                {{ channel }}
              </option>
            </select>
          </div>

          <div class="grid gap-2">
            <h3 class="text-sm font-medium">Config</h3>
            <JsonSchemaForm
              v-model="configValues"
              :schema="selectedConnector?.config_schema"
            />
          </div>

          <div class="grid gap-2">
            <h3 class="text-sm font-medium">Secrets</h3>
            <JsonSchemaForm
              v-model="secretValues"
              :schema="selectedConnector?.secrets_schema"
              secret
            />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="secret-ref">
              External secret ref
            </label>
            <Input
              id="secret-ref"
              v-model="secretRef"
              placeholder="Optional vault/key reference"
            />
          </div>

          <SheetFooter class="mt-2 gap-2 p-0 sm:flex-row sm:justify-end">
            <Button
              type="submit"
              :disabled="
                !selectedConnector || createConnectionMutation.isPending.value
              "
            >
              <PlugZap class="size-4" />
              {{
                createConnectionMutation.isPending.value ? "Creating" : "Create"
              }}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>

    <AlertDialog
      :open="connectionPendingDeletion !== null"
      @update:open="
        (open) => {
          if (!open) connectionPendingDeletion = null;
        }
      "
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete connection</AlertDialogTitle>
          <AlertDialogDescription>
            The connection must stay disabled. Delete cannot be undone if there
            is no send history.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            :disabled="deleteMutation.isPending.value"
            @click="deleteConnection"
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </section>
</template>
