<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { FileUp, PlugZap, RefreshCcw, Upload } from "lucide-vue-next";
import { toast } from "vue-sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { communicationApi } from "@/modules/communication/api";
import type { JsonObject } from "@/modules/communication/api";
import JsonSchemaForm from "@/modules/communication/components/JsonSchemaForm.vue";
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";
import StatusBadge from "@/modules/communication/components/StatusBadge.vue";
import {
  apiErrorMessage,
  buildJsonSchemaDefaults,
  compactJsonObject,
} from "@/modules/communication/lib";

const queryClient = useQueryClient();

const yamlContent = ref("");
const yamlFileName = ref("");
const selectedConnectorId = ref("");
const connectionCode = ref("");
const connectionName = ref("");
const channelCode = ref("");
const secretRef = ref("");
const configValues = ref<JsonObject>({});
const secretValues = ref<JsonObject>({});

const catalogQuery = useQuery({
  queryKey: ["communication", "provider-catalog"],
  queryFn: communicationApi.listProviderCatalog,
  retry: false,
});

const connectionsQuery = useQuery({
  queryKey: ["communication", "provider-connections"],
  queryFn: communicationApi.listProviderConnections,
  retry: false,
});

const importMutation = useMutation({
  mutationFn: (content: string) =>
    communicationApi.importProviderConnectorYaml(content),
});

const createConnectionMutation = useMutation({
  mutationFn: communicationApi.createProviderConnection,
});

const connectors = computed(() => catalogQuery.data.value?.connectors ?? []);
const messageTypes = computed(
  () => catalogQuery.data.value?.message_types ?? [],
);
const connections = computed(() => connectionsQuery.data.value?.items ?? []);
const selectedConnector = computed(() =>
  connectors.value.find(
    (connector) =>
      connector.provider_connector_id === selectedConnectorId.value,
  ),
);
const selectedConnectorMessageTypes = computed(() =>
  messageTypes.value.filter(
    (messageType) =>
      messageType.provider_connector_id === selectedConnectorId.value,
  ),
);

watch(
  connectors,
  (items) => {
    if (!items.length) {
      selectedConnectorId.value = "";
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

watch(selectedConnectorId, () => {
  const connector = selectedConnector.value;

  if (!connector) {
    connectionCode.value = "";
    connectionName.value = "";
    channelCode.value = "";
    configValues.value = {};
    secretValues.value = {};
    return;
  }

  connectionCode.value = `${connector.provider_code}_main`;
  connectionName.value = `${connector.provider_name} main`;
  channelCode.value = connector.channels[0] ?? "";
  configValues.value = buildJsonSchemaDefaults(connector.config_schema);
  secretValues.value = buildJsonSchemaDefaults(connector.secrets_schema);
});

async function refreshProviders() {
  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: ["communication", "provider-catalog"],
    }),
    queryClient.invalidateQueries({
      queryKey: ["communication", "provider-connections"],
    }),
  ]);
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
    yamlContent.value = "";
    yamlFileName.value = "";
    selectedConnectorId.value = connector.provider_connector_id;
    await refreshProviders();
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

async function createConnection() {
  const connector = selectedConnector.value;

  if (!connector) {
    toast.error("Select a provider connector.");
    return;
  }

  try {
    await createConnectionMutation.mutateAsync({
      provider_connector_id: connector.provider_connector_id,
      connection_code: connectionCode.value.trim(),
      connection_name: connectionName.value.trim(),
      channel_code: channelCode.value,
      config: compactJsonObject(configValues.value),
      secrets: compactJsonObject(secretValues.value),
      secret_ref: secretRef.value.trim() || null,
    });
    toast.success("Provider connect created.");
    await refreshProviders();
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

function handleYamlFileChange(event: Event) {
  const target = event.target;

  if (!(target instanceof HTMLInputElement) || !target.files?.length) {
    return;
  }

  const file = target.files[0];
  const reader = new FileReader();

  reader.onload = () => {
    yamlContent.value = String(reader.result ?? "");
    yamlFileName.value = file.name;
  };

  reader.readAsText(file);
}

function selectConnector(connectorId: string) {
  selectedConnectorId.value = connectorId;
}

function formatDate(value: string) {
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
        title="Providers"
        description="Import provider YAML specs, review supported channels and message types, then create tenant connects for outbound sends."
      />
      <Button
        type="button"
        variant="outline"
        :disabled="
          catalogQuery.isFetching.value || connectionsQuery.isFetching.value
        "
        @click="refreshProviders"
      >
        <RefreshCcw
          class="size-4"
          :class="{
            'animate-spin':
              catalogQuery.isFetching.value ||
              connectionsQuery.isFetching.value,
          }"
        />
        Refresh
      </Button>
    </div>

    <Alert
      v-if="catalogQuery.error.value || connectionsQuery.error.value"
      variant="destructive"
    >
      <AlertDescription>
        {{
          apiErrorMessage(
            catalogQuery.error.value ?? connectionsQuery.error.value,
          )
        }}
      </AlertDescription>
    </Alert>

    <div
      class="grid min-h-0 flex-1 gap-4 overflow-hidden xl:grid-cols-[1.1fr_0.9fr]"
    >
      <div class="flex min-h-0 flex-col gap-4 overflow-auto pr-1">
        <div class="grid gap-3 rounded-lg border p-4">
          <div class="flex items-center justify-between gap-3">
            <div class="grid gap-1">
              <h3 class="text-sm font-semibold">Import YAML connector</h3>
              <p class="text-sm text-muted-foreground">
                Upload a provider specification from the communication catalog.
              </p>
            </div>
            <FileUp class="size-5 text-muted-foreground" />
          </div>
          <Input
            type="file"
            accept=".yaml,.yml,text/yaml,application/x-yaml"
            @change="handleYamlFileChange"
          />
          <p v-if="yamlFileName" class="text-xs text-muted-foreground">
            Loaded {{ yamlFileName }}
          </p>
          <Textarea
            v-model="yamlContent"
            class="min-h-52 font-mono text-xs"
            placeholder="provider_code: ..."
          />
          <div class="flex justify-end">
            <Button
              type="button"
              :disabled="importMutation.isPending.value"
              @click="importYaml"
            >
              <Upload class="size-4" />
              {{ importMutation.isPending.value ? "Importing" : "Import" }}
            </Button>
          </div>
        </div>

        <div class="grid gap-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold">Connector catalog</h3>
            <Badge variant="outline">{{ connectors.length }} connectors</Badge>
          </div>
          <div class="grid gap-3 md:grid-cols-2">
            <Card
              v-for="connector in connectors"
              :key="connector.provider_connector_id"
              class="cursor-pointer transition-colors hover:bg-accent/40"
              :class="{
                'border-primary bg-accent/50':
                  selectedConnectorId === connector.provider_connector_id,
              }"
              @click="selectConnector(connector.provider_connector_id)"
            >
              <CardHeader class="gap-2">
                <div class="flex items-start justify-between gap-3">
                  <div class="grid gap-1">
                    <CardTitle class="text-base">
                      {{ connector.provider_name }}
                    </CardTitle>
                    <CardDescription>
                      {{ connector.provider_code }} · {{ connector.version }}
                    </CardDescription>
                  </div>
                  <StatusBadge :status="connector.status" />
                </div>
              </CardHeader>
              <CardContent class="grid gap-3">
                <div class="flex flex-wrap gap-1">
                  <Badge
                    v-for="channel in connector.channels"
                    :key="channel"
                    variant="secondary"
                  >
                    {{ channel }}
                  </Badge>
                </div>
                <div class="grid gap-1 text-xs text-muted-foreground">
                  <span>{{ connector.connector_type }}</span>
                  <span>Updated {{ formatDate(connector.updated_at) }}</span>
                </div>
              </CardContent>
            </Card>
          </div>
          <p
            v-if="!catalogQuery.isLoading.value && connectors.length === 0"
            class="text-sm text-muted-foreground"
          >
            No provider connectors imported yet.
          </p>
        </div>
      </div>

      <div class="flex min-h-0 flex-col gap-4 overflow-auto pl-1">
        <form
          class="grid gap-4 rounded-lg border p-4"
          @submit.prevent="createConnection"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="grid gap-1">
              <h3 class="text-sm font-semibold">Create connect</h3>
              <p class="text-sm text-muted-foreground">
                Select a connector and fill config/secrets required by its YAML
                schema.
              </p>
            </div>
            <PlugZap class="size-5 text-muted-foreground" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="connector">Connector</label>
            <select
              id="connector"
              v-model="selectedConnectorId"
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="connector in connectors"
                :key="connector.provider_connector_id"
                :value="connector.provider_connector_id"
              >
                {{ connector.provider_name }} ({{ connector.provider_code }})
              </option>
            </select>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
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
            <label class="text-sm font-medium" for="channel">Channel</label>
            <select
              id="channel"
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
            <h4 class="text-sm font-medium">Config</h4>
            <JsonSchemaForm
              v-model="configValues"
              :schema="selectedConnector?.config_schema"
            />
          </div>

          <div class="grid gap-2">
            <h4 class="text-sm font-medium">Secrets</h4>
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

          <Button
            type="submit"
            :disabled="
              !selectedConnector || createConnectionMutation.isPending.value
            "
          >
            <PlugZap class="size-4" />
            {{
              createConnectionMutation.isPending.value
                ? "Creating"
                : "Create connect"
            }}
          </Button>
        </form>

        <div class="grid gap-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold">Existing connects</h3>
            <Badge variant="outline">{{ connections.length }} connects</Badge>
          </div>
          <Card
            v-for="connection in connections"
            :key="connection.provider_connection_id"
          >
            <CardHeader class="gap-2">
              <div class="flex items-start justify-between gap-3">
                <div class="grid gap-1">
                  <CardTitle class="text-base">
                    {{ connection.connection_name }}
                  </CardTitle>
                  <CardDescription>
                    {{ connection.connection_code }} ·
                    {{ connection.channel_code }}
                  </CardDescription>
                </div>
                <StatusBadge :status="connection.status" />
              </div>
            </CardHeader>
            <CardContent class="grid gap-2 text-sm text-muted-foreground">
              <div class="flex flex-wrap gap-2">
                <Badge variant="secondary">
                  {{
                    connectors.find(
                      (item) =>
                        item.provider_connector_id ===
                        connection.provider_connector_id,
                    )?.provider_name ?? "Connector"
                  }}
                </Badge>
                <Badge v-if="connection.has_secrets" variant="outline">
                  Secrets configured
                </Badge>
                <Badge v-if="connection.secret_ref" variant="outline">
                  {{ connection.secret_ref }}
                </Badge>
              </div>
              <span>Updated {{ formatDate(connection.updated_at) }}</span>
            </CardContent>
          </Card>
          <p
            v-if="!connectionsQuery.isLoading.value && connections.length === 0"
            class="text-sm text-muted-foreground"
          >
            No connects created yet.
          </p>
        </div>

        <div
          v-if="selectedConnectorMessageTypes.length"
          class="grid gap-3 rounded-lg border p-4"
        >
          <h3 class="text-sm font-semibold">Message types</h3>
          <div
            v-for="messageType in selectedConnectorMessageTypes"
            :key="messageType.provider_message_type_id"
            class="flex items-center justify-between gap-3 rounded-md border px-3 py-2"
          >
            <div class="grid gap-1">
              <span class="text-sm font-medium">{{ messageType.name }}</span>
              <span class="text-xs text-muted-foreground">
                {{ messageType.message_type_code }} ·
                {{ messageType.channel_code }}
              </span>
            </div>
            <StatusBadge
              :status="messageType.is_active ? 'ACTIVE' : 'DISABLED'"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
