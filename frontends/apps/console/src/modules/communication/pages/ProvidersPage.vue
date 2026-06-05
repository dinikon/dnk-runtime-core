<script setup lang="ts">
import { computed, ref } from "vue";
import {
  getCoreRowModel,
  getFilteredRowModel,
  useVueTable,
  type ColumnDef,
} from "@tanstack/vue-table";
import {
  CheckCircle2,
  PauseCircle,
  RefreshCcw,
  Trash2,
  Upload,
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
  ProviderConnector,
  ProviderConnectorMutableStatus,
} from "@/modules/communication/api";
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";
import ProvidersToolBar from "@/modules/communication/components/ProvidersToolBar.vue";
import StatusBadge from "@/modules/communication/components/StatusBadge.vue";
import { apiErrorMessage } from "@/modules/communication/lib";
import { useDeleteProviderConnectorMutation } from "@/modules/communication/mutations/use-delete-provider-connector";
import { useImportProviderConnectorYamlMutation } from "@/modules/communication/mutations/use-import-provider-connector-yaml";
import { useUpdateProviderConnectorStatusMutation } from "@/modules/communication/mutations/use-update-provider-connector-status";
import { useProviderCatalogQuery } from "@/modules/communication/queries/use-provider-catalog-query";

const route = useRoute();
const router = useRouter();

const yamlContent = ref("");
const pendingConnectorId = ref<string | null>(null);
const connectorPendingDeletion = ref<ProviderConnector | null>(null);

const catalogQuery = useProviderCatalogQuery();
const importMutation = useImportProviderConnectorYamlMutation();
const updateStatusMutation = useUpdateProviderConnectorStatusMutation();
const deleteMutation = useDeleteProviderConnectorMutation();

const connectors = computed(() =>
  (catalogQuery.data.value?.connectors ?? []).filter(
    (connector) => !connector.status.startsWith("ARCHIV"),
  ),
);
const messageTypes = computed(
  () => catalogQuery.data.value?.message_types ?? [],
);
const searchQuery = computed(() => {
  const value = route.query.q;
  return typeof value === "string" ? value : "";
});
const isImportSheetOpen = computed({
  get: () => route.query.import === "provider",
  set: (value: boolean) => {
    patchQuery({ import: value ? "provider" : undefined });
  },
});
const messageTypeCounts = computed(() =>
  messageTypes.value.reduce<Record<string, number>>((counts, messageType) => {
    const current = counts[messageType.provider_connector_id] ?? 0;
    counts[messageType.provider_connector_id] = current + 1;
    return counts;
  }, {}),
);
const actionPending = computed(
  () => updateStatusMutation.isPending.value || deleteMutation.isPending.value,
);
const columns: ColumnDef<ProviderConnector>[] = [
  {
    id: "provider",
    accessorFn: (connector) =>
      `${connector.provider_name} ${connector.provider_code} ${connector.version}`,
    header: "Provider",
  },
  {
    id: "channels",
    accessorFn: (connector) => connector.channels.join(" "),
    header: "Channels",
  },
  {
    id: "connector_type",
    accessorKey: "connector_type",
    header: "Type",
  },
  {
    id: "message_types",
    accessorFn: (connector) =>
      String(messageTypeCounts.value[connector.provider_connector_id] ?? 0),
    header: "Message types",
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
  data: connectors,
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

async function importYaml() {
  const content = yamlContent.value.trim();

  if (!content) {
    toast.error("Select a YAML file or paste YAML content.");
    return;
  }

  try {
    const connector = await importMutation.mutateAsync(content);
    toast.success(`${connector.provider_name} imported.`);
    resetImportForm();
    isImportSheetOpen.value = false;
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

async function updateConnectorStatus(
  connector: ProviderConnector,
  status: ProviderConnectorMutableStatus,
) {
  pendingConnectorId.value = connector.provider_connector_id;

  try {
    const updatedConnector = await updateStatusMutation.mutateAsync({
      provider_connector_id: connector.provider_connector_id,
      status,
    });
    toast.success(
      `${updatedConnector.provider_name} is ${status.toLowerCase()}.`,
    );
  } catch (error) {
    toast.error(apiErrorMessage(error));
  } finally {
    pendingConnectorId.value = null;
  }
}

async function deleteConnector() {
  const connector = connectorPendingDeletion.value;

  if (!connector) {
    return;
  }

  pendingConnectorId.value = connector.provider_connector_id;

  try {
    await deleteMutation.mutateAsync(connector.provider_connector_id);
    toast.success(`${connector.provider_name} deleted.`);
    connectorPendingDeletion.value = null;
  } catch (error) {
    toast.error(apiErrorMessage(error));
  } finally {
    pendingConnectorId.value = null;
  }
}

function resetImportForm() {
  yamlContent.value = "";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function messageTypeCount(connector: ProviderConnector) {
  return messageTypeCounts.value[connector.provider_connector_id] ?? 0;
}

function isConnectorPending(connector: ProviderConnector) {
  return (
    pendingConnectorId.value === connector.provider_connector_id &&
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
        title="Providers"
        description="Import provider connector templates, inspect supported channels and manage provider lifecycle status."
      />
      <Button
        type="button"
        variant="outline"
        :disabled="catalogQuery.isFetching.value"
        @click="catalogQuery.refetch()"
      >
        <RefreshCcw
          class="size-4"
          :class="{ 'animate-spin': catalogQuery.isFetching.value }"
        />
        Refresh
      </Button>
    </div>

    <Alert v-if="catalogQuery.error.value" variant="destructive">
      <AlertDescription>
        {{ apiErrorMessage(catalogQuery.error.value) }}
      </AlertDescription>
    </Alert>

    <ProvidersToolBar />

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
                'w-44': header.column.id === 'status',
                'w-48': header.column.id === 'updated_at',
              }"
            >
              {{ header.column.columnDef.header }}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="catalogQuery.isLoading.value">
            <TableRow v-for="index in 8" :key="index">
              <TableCell>
                <div class="grid gap-2">
                  <Skeleton class="h-4 w-40" />
                  <Skeleton class="h-3 w-28" />
                </div>
              </TableCell>
              <TableCell>
                <Skeleton class="h-5 w-36" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-24" />
              </TableCell>
              <TableCell>
                <Skeleton class="h-4 w-16" />
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
            No providers found.
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
              <div v-if="cell.column.id === 'provider'" class="grid gap-1">
                <span class="font-medium">
                  {{ row.original.provider_name }}
                </span>
                <span class="text-xs text-muted-foreground">
                  {{ row.original.provider_code }} · {{ row.original.version }}
                </span>
              </div>

              <div
                v-else-if="cell.column.id === 'channels'"
                class="flex max-w-72 flex-wrap gap-1"
              >
                <Badge
                  v-for="channel in row.original.channels"
                  :key="channel"
                  variant="secondary"
                >
                  {{ channel }}
                </Badge>
              </div>

              <span
                v-else-if="cell.column.id === 'connector_type'"
                class="text-sm"
              >
                {{ row.original.connector_type }}
              </span>

              <span
                v-else-if="cell.column.id === 'message_types'"
                class="text-sm"
              >
                {{ messageTypeCount(row.original) }}
              </span>

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
                  :disabled="isConnectorPending(row.original)"
                  @click="updateConnectorStatus(row.original, 'DISABLED')"
                >
                  <PauseCircle class="size-4" />
                  Deactivate
                </Button>
                <Button
                  v-if="row.original.status === 'DISABLED'"
                  type="button"
                  variant="outline"
                  size="sm"
                  :disabled="isConnectorPending(row.original)"
                  @click="updateConnectorStatus(row.original, 'ACTIVE')"
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
                  :disabled="isConnectorPending(row.original)"
                  @click="connectorPendingDeletion = row.original"
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

    <Sheet v-model:open="isImportSheetOpen">
      <SheetContent
        class="w-[min(32rem,100vw)] gap-2 overflow-y-auto p-4 sm:max-w-lg"
      >
        <SheetHeader class="gap-1 p-0 pr-8">
          <SheetTitle>Import provider</SheetTitle>
          <SheetDescription>
            Paste provider connector YAML spec.
          </SheetDescription>
        </SheetHeader>

        <form class="grid gap-2" @submit.prevent="importYaml">
          <div class="grid min-h-0 flex-1 gap-2">
            <label class="text-sm font-medium" for="provider-yaml-content">
              YAML content
            </label>
            <Textarea
              id="provider-yaml-content"
              v-model="yamlContent"
              class="min-h-64 resize-y font-mono text-xs"
              placeholder="provider_code: ..."
            />
          </div>

          <SheetFooter class="mt-2 gap-2 p-0 sm:flex-row sm:justify-between">
            <Button type="button" variant="outline" @click="resetImportForm">
              Clear
            </Button>
            <Button type="submit" :disabled="importMutation.isPending.value">
              <Upload class="size-4" />
              {{ importMutation.isPending.value ? "Importing" : "Import" }}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>

    <AlertDialog
      :open="connectorPendingDeletion !== null"
      @update:open="
        (open) => {
          if (!open) connectorPendingDeletion = null;
        }
      "
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete provider</AlertDialogTitle>
          <AlertDialogDescription>
            The provider must stay disabled. Delete cannot be undone if there is
            no usage history.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            :disabled="deleteMutation.isPending.value"
            @click="deleteConnector"
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </section>
</template>
