<script setup lang="ts">
import {computed, reactive, ref, watch, type Component} from "vue";
import {useRoute, useRouter} from "vue-router";
import {
  Check,
  ChevronRight,
  Copy,
  KeyRound,
  LayoutGrid,
  Loader2,
  Package,
  Plus,
  Search,
  Upload,
  Wrench,
} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import type {ProviderConnector} from "@/api/communication";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {Alert, AlertDescription} from "@/components/ui/alert";
import {Button} from "@/components/ui/button";
import {Checkbox} from "@/components/ui/checkbox";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle} from "@/components/ui/sheet";
import {Skeleton} from "@/components/ui/skeleton";
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs";
import {Textarea} from "@/components/ui/textarea";
import {SettingsLayout} from "@/layouts";
import {
  coerceSchemaValues,
  initialSchemaForm,
  schemaFields,
  type SchemaField,
  type SchemaFormValues,
} from "./schemaForm";
import {
  useCreateProviderConnectionMutation,
  useImportProviderConnectorMutation,
  useProviderConnectionsQuery,
  useProviderConnectorsQuery,
} from "./providerQueries";

type ProviderTab = "available" | "connections" | "custom";

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();

const providerConnectorsQuery = useProviderConnectorsQuery();
const providerConnectionsQuery = useProviderConnectionsQuery();
const importConnectorMutation = useImportProviderConnectorMutation();
const createConnectionMutation = useCreateProviderConnectionMutation();

const providerTabs: Array<{ value: ProviderTab; label: string; icon: Component }> = [
  {value: "available", label: "Available", icon: Package},
  {value: "connections", label: "Connections", icon: LayoutGrid},
  {value: "custom", label: "Create custom", icon: Wrench},
];

const providerTones = [
  "border-blue-100 bg-blue-50 text-blue-700",
  "border-emerald-100 bg-emerald-50 text-emerald-700",
  "border-orange-100 bg-orange-50 text-orange-700",
  "border-sky-100 bg-sky-50 text-sky-700",
  "border-violet-100 bg-violet-50 text-violet-700",
  "border-rose-100 bg-rose-50 text-rose-700",
];

const providerYamlExample = `provider_code: custom_sms
provider_name: Custom SMS
version: "1.0.0"
connector_type: YAML_HTTP

channels:
  - SMS

auth:
  type: bearer
  token_secret_key: api_key

config_schema:
  type: object
  properties:
    sender:
      type: string
      title: Sender

secrets_schema:
  type: object
  required:
    - api_key
  properties:
    api_key:
      type: string
      title: API key
      format: password

message_types:
  - code: sms_text
    channel: SMS
    name: Text message
    field_schema:
      type: object
      required:
        - text
      properties:
        text:
          type: string
          title: Text
    ui_schema: {}
    send:
      transport: http
      method: POST
      url: https://example.com/messages
      headers:
        Content-Type: application/json
      body:
        to: "{{ recipient.address }}"
        text: "{{ template.text }}"
`;

const activeTab = computed<ProviderTab>({
  get: () => {
    const queryTab = Array.isArray(route.query.tab) ? route.query.tab[0] : route.query.tab;
    return isProviderTab(queryTab) ? queryTab : "available";
  },
  set: (tab) => {
    const query = {...route.query};
    if (tab === "available") {
      delete query.tab;
    } else {
      query.tab = tab;
    }
    void router.replace({query});
  },
});

const providerSearch = ref("");
const connectionSearch = ref("");
const yamlContent = ref("");
const importFormError = ref<string | null>(null);
const didCopyExample = ref(false);

const isConnectionOpen = ref(false);
const connectionError = ref<string | null>(null);
const connectionForm = reactive({
  provider_connector_id: "",
  connection_code: "",
  connection_name: "",
  channel_code: "",
});
const configValues = ref<SchemaFormValues>({});
const secretValues = ref<SchemaFormValues>({});
const isRedirectingToLogin = ref(false);

const connectors = computed(() => providerConnectorsQuery.data.value?.connectors ?? []);
const messageTypes = computed(() => providerConnectorsQuery.data.value?.message_types ?? []);
const connections = computed(() => providerConnectionsQuery.data.value?.items ?? []);

const connectorById = computed(() => new Map(
  connectors.value.map((connector) => [connector.provider_connector_id, connector]),
));

const filteredConnectors = computed(() => connectors.value.filter((connector) => (
  matchesSearch([
    connector.provider_name,
    connector.provider_code,
    connector.connector_type,
    connector.status,
    ...connector.channels,
  ], providerSearch.value)
)));

const connectorGroups = computed(() => {
  const groups = new Map<string, ProviderConnector[]>();

  for (const connector of filteredConnectors.value) {
    const label = formatChannel(connector.channels[0] ?? connector.connector_type ?? "Providers");
    groups.set(label, [...groups.get(label) ?? [], connector]);
  }

  return Array.from(groups, ([label, items]) => ({label, items}));
});

const filteredConnections = computed(() => connections.value.filter((connection) => {
  const connector = connectorById.value.get(connection.provider_connector_id);
  return matchesSearch([
    connection.connection_name,
    connection.connection_code,
    connection.channel_code,
    connection.status,
    connector?.provider_name,
    connector?.provider_code,
  ], connectionSearch.value);
}));

const selectedConnector = computed(() => (
  connectorById.value.get(connectionForm.provider_connector_id) ?? null
));
const selectedMessageTypes = computed(() => messageTypes.value.filter((type) => (
  type.provider_connector_id === selectedConnector.value?.provider_connector_id
)));
const selectedConfigFields = computed(() => schemaFields(selectedConnector.value?.config_schema));
const selectedSecretFields = computed(() => schemaFields(selectedConnector.value?.secrets_schema));

const pageError = computed(() => {
  if (providerConnectorsQuery.error.value) {
    return getApiErrorMessage(providerConnectorsQuery.error.value, "Could not load providers.");
  }
  if (providerConnectionsQuery.error.value) {
    return getApiErrorMessage(providerConnectionsQuery.error.value, "Could not load provider connections.");
  }
  return null;
});
const importDisplayError = computed(() => (
  importFormError.value
  ?? (importConnectorMutation.error.value
    ? getApiErrorMessage(importConnectorMutation.error.value, "Could not import provider YAML.")
    : null)
));
const connectionDisplayError = computed(() => (
  connectionError.value
  ?? (createConnectionMutation.error.value
    ? getApiErrorMessage(createConnectionMutation.error.value, "Could not create provider connection.")
    : null)
));
const isLoadingProviders = computed(() => providerConnectorsQuery.isLoading.value);
const isLoadingConnections = computed(() => providerConnectionsQuery.isLoading.value);
const isImporting = computed(() => importConnectorMutation.isPending.value);
const isCreatingConnection = computed(() => createConnectionMutation.isPending.value);

watch(
  [
    providerConnectorsQuery.error,
    providerConnectionsQuery.error,
    importConnectorMutation.error,
    createConnectionMutation.error,
  ],
  (errors) => {
    if (errors.some((error) => getApiErrorStatus(error) === 401)) {
      void redirectToLogin();
    }
  },
);

watch(selectedConnector, (connector, previousConnector) => {
  if (
    !isConnectionOpen.value
    || !connector
    || connector.provider_connector_id === previousConnector?.provider_connector_id
  ) {
    return;
  }

  applyConnectorDefaults(connector);
});

function setActiveTab(value: string | number) {
  if (isProviderTab(value)) {
    activeTab.value = value;
  }
}

function isProviderTab(value: unknown): value is ProviderTab {
  return value === "available" || value === "connections" || value === "custom";
}

function matchesSearch(values: Array<string | null | undefined>, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }

  return values.some((value) => (value ?? "").toLowerCase().includes(normalizedQuery));
}

function openConnectionSheet(connector?: ProviderConnector) {
  const target = connector ?? connectors.value[0] ?? null;
  if (!target) {
    return;
  }

  createConnectionMutation.reset();
  connectionError.value = null;
  connectionForm.provider_connector_id = target.provider_connector_id;
  applyConnectorDefaults(target);
  isConnectionOpen.value = true;
}

function applyConnectorDefaults(connector: ProviderConnector) {
  const channel = connector.channels[0] ?? "";
  connectionForm.channel_code = channel;
  connectionForm.connection_code = defaultConnectionCode(connector, channel);
  connectionForm.connection_name = `${connector.provider_name} ${formatChannel(channel)}`.trim();
  configValues.value = initialSchemaForm(connector.config_schema);
  secretValues.value = initialSchemaForm(connector.secrets_schema);
}

function defaultConnectionCode(connector: ProviderConnector, channel: string): string {
  return `${connector.provider_code}_${channel || "main"}`
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

async function submitConnection() {
  createConnectionMutation.reset();
  connectionError.value = null;

  if (!selectedConnector.value) {
    connectionError.value = "Provider connector is required.";
    return;
  }

  if (
    !connectionForm.connection_code.trim()
    || !connectionForm.connection_name.trim()
    || !connectionForm.channel_code
  ) {
    connectionError.value = "Connection code, name, and channel are required.";
    return;
  }

  try {
    await createConnectionMutation.mutateAsync({
      provider_connector_id: connectionForm.provider_connector_id,
      connection_code: connectionForm.connection_code.trim(),
      connection_name: connectionForm.connection_name.trim(),
      channel_code: connectionForm.channel_code,
      config: coerceSchemaValues(selectedConnector.value.config_schema, configValues.value),
      secrets: coerceSchemaValues(selectedConnector.value.secrets_schema, secretValues.value),
    });
    isConnectionOpen.value = false;
    activeTab.value = "connections";
  } catch {
    // The mutation exposes the API error through connectionDisplayError.
  }
}

async function submitImport() {
  importConnectorMutation.reset();
  importFormError.value = null;

  if (!yamlContent.value.trim()) {
    importFormError.value = "Provider YAML is required.";
    return;
  }

  try {
    await importConnectorMutation.mutateAsync(yamlContent.value);
    yamlContent.value = "";
    activeTab.value = "available";
  } catch {
    // The mutation exposes the API error through importDisplayError.
  }
}

async function copyYamlExample() {
  yamlContent.value = providerYamlExample;
  didCopyExample.value = false;

  if (navigator.clipboard) {
    await navigator.clipboard.writeText(providerYamlExample);
  }

  didCopyExample.value = true;
  window.setTimeout(() => {
    didCopyExample.value = false;
  }, 1200);
}

function connectorName(providerConnectorId: string): string {
  return connectorById.value.get(providerConnectorId)?.provider_name ?? "Provider";
}

function messageTypeCount(connector: ProviderConnector): number {
  return messageTypes.value.filter((type) => type.provider_connector_id === connector.provider_connector_id).length;
}

function providerInitials(connector: ProviderConnector): string {
  const source = connector.provider_name.trim() || connector.provider_code;
  const words = source.split(/\s+/).filter(Boolean);
  const initials = words.slice(0, 2).map((word) => word[0]?.toUpperCase()).join("");
  return initials || connector.provider_code.slice(0, 2).toUpperCase() || "P";
}

function providerTone(connector: ProviderConnector): string {
  const hash = Array.from(connector.provider_code).reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return providerTones[hash % providerTones.length];
}

function formatChannel(value: string): string {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusLabel(value: string): string {
  return formatChannel(value || "unknown");
}

function schemaInputType(field: SchemaField): string {
  if (field.type === "integer" || field.type === "number") {
    return "number";
  }
  return field.type === "password" ? "password" : "text";
}

function stringSchemaValue(values: SchemaFormValues, key: string): string {
  const value = values[key];
  return typeof value === "string" ? value : "";
}

function booleanSchemaValue(values: SchemaFormValues, key: string): boolean {
  return values[key] === true;
}

function updateConfigValue(key: string, value: string | number) {
  configValues.value[key] = String(value);
}

function updateSecretValue(key: string, value: string | number) {
  secretValues.value[key] = String(value);
}

function updateConfigBoolean(key: string, value: boolean) {
  configValues.value[key] = value;
}

function updateSecretBoolean(key: string, value: boolean) {
  secretValues.value[key] = value;
}

async function redirectToLogin() {
  if (isRedirectingToLogin.value) {
    return;
  }

  isRedirectingToLogin.value = true;
  sessionStore.clearSession();
  await router.push("/login");
}
</script>

<template>
  <SettingsLayout
      title="Communication Providers"
      active-item="communication-providers"
      :breadcrumbs="[{label: 'Workspace'}, {label: 'Communication'}, {label: 'Providers'}]"
  >
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div class="grid gap-1">
          <h1 class="text-base font-semibold">Providers</h1>
          <p class="text-sm text-muted-foreground">Connectors, connections, and custom provider definitions.</p>
        </div>
      </header>

      <Alert v-if="pageError" variant="destructive">
        <AlertDescription>{{ pageError }}</AlertDescription>
      </Alert>

      <Tabs :model-value="activeTab" @update:model-value="setActiveTab">
        <TabsList class="w-full">
          <TabsTrigger v-for="tab in providerTabs" :key="tab.value" :value="tab.value">
            <component :is="tab.icon"/>
            {{ tab.label }}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="available" class="pt-6">
          <div class="grid gap-5">
            <div class="flex items-center gap-2">
              <div class="relative flex-1">
                <Search class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"/>
                <Input v-model="providerSearch" class="h-8 pl-8" placeholder="Search a provider"/>
              </div>
            </div>

            <div v-if="isLoadingProviders" class="grid gap-3 sm:grid-cols-2">
              <Skeleton v-for="index in 4" :key="index" class="h-24 rounded-lg"/>
            </div>

            <div v-else-if="connectors.length === 0" class="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              No providers imported.
            </div>

            <div v-else-if="filteredConnectors.length === 0" class="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              No providers match your search.
            </div>

            <template v-else>
              <section v-for="group in connectorGroups" :key="group.label" class="grid gap-3">
                <h2 class="text-sm font-medium">{{ group.label }}</h2>
                <div class="grid gap-3 sm:grid-cols-2">
                  <button
                      v-for="connector in group.items"
                      :key="connector.provider_connector_id"
                      type="button"
                      class="group flex min-h-24 items-start gap-3 rounded-lg border bg-card p-3 text-left shadow-xs transition-colors hover:border-foreground/30 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      @click="openConnectionSheet(connector)"
                  >
                    <span
                        class="flex size-9 shrink-0 items-center justify-center rounded-md border text-xs font-semibold"
                        :class="providerTone(connector)"
                    >
                      {{ providerInitials(connector) }}
                    </span>
                    <span class="grid min-w-0 flex-1 gap-1">
                      <span class="flex items-start justify-between gap-2">
                        <span class="truncate text-sm font-medium">{{ connector.provider_name }}</span>
                        <ChevronRight class="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"/>
                      </span>
                      <span class="line-clamp-2 text-xs leading-5 text-muted-foreground">
                        {{ connector.provider_code }} · {{ connector.version }} · {{ messageTypeCount(connector) }} message types
                      </span>
                      <span class="flex flex-wrap gap-1 pt-1">
                        <span
                            v-for="channel in connector.channels"
                            :key="channel"
                            class="rounded border bg-background px-1.5 py-0.5 text-[11px] leading-none text-muted-foreground"
                        >
                          {{ formatChannel(channel) }}
                        </span>
                      </span>
                    </span>
                  </button>
                </div>
              </section>
            </template>
          </div>
        </TabsContent>

        <TabsContent value="connections" class="pt-6">
          <div class="grid gap-5">
            <div class="grid gap-1">
              <h2 class="text-sm font-semibold">Provider connections</h2>
              <p class="text-sm text-muted-foreground">Connections created from available provider connectors.</p>
            </div>

            <div class="relative">
              <Search class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"/>
              <Input v-model="connectionSearch" class="h-8 pl-8" placeholder="Search a connection"/>
            </div>

            <div v-if="isLoadingConnections" class="grid gap-2">
              <Skeleton v-for="index in 4" :key="index" class="h-10 rounded-md"/>
            </div>

            <div v-else class="overflow-hidden rounded-lg border">
              <div class="grid grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_88px_92px] gap-4 border-b px-3 py-2 text-xs font-medium text-muted-foreground">
                <div>Name</div>
                <div>Provider</div>
                <div>Channel</div>
                <div>Status</div>
              </div>

              <div v-if="connections.length === 0" class="px-3 py-10 text-center text-sm text-muted-foreground">
                No connections.
              </div>

              <div v-else-if="filteredConnections.length === 0" class="px-3 py-10 text-center text-sm text-muted-foreground">
                No connections match your search.
              </div>

              <template v-else>
                <div
                    v-for="connection in filteredConnections"
                    :key="connection.provider_connection_id"
                    class="grid min-h-10 grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_88px_92px] items-center gap-4 border-b px-3 py-2 text-sm last:border-b-0"
                >
                  <div class="min-w-0">
                    <div class="truncate font-medium">{{ connection.connection_name }}</div>
                    <div class="truncate text-xs text-muted-foreground">{{ connection.connection_code }}</div>
                  </div>
                  <div class="truncate text-muted-foreground">{{ connectorName(connection.provider_connector_id) }}</div>
                  <div class="text-muted-foreground">{{ formatChannel(connection.channel_code) }}</div>
                  <div>
                    <span class="rounded border bg-background px-1.5 py-0.5 text-xs text-muted-foreground">
                      {{ statusLabel(connection.status) }}
                    </span>
                  </div>
                </div>
              </template>
            </div>

            <div class="flex justify-end">
              <Button type="button" variant="outline" size="sm" @click="activeTab = 'available'">
                <Plus class="size-4"/>
                Add connection
              </Button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="custom" class="pt-6">
          <form class="grid gap-5" @submit.prevent="submitImport">
            <div class="grid gap-1">
              <h2 class="text-sm font-semibold">Create a custom provider</h2>
              <p class="text-sm text-muted-foreground">Import a YAML provider definition for private connections.</p>
            </div>

            <Alert v-if="importDisplayError" variant="destructive">
              <AlertDescription>{{ importDisplayError }}</AlertDescription>
            </Alert>

            <div class="relative">
              <Textarea
                  v-model="yamlContent"
                  class="min-h-80 resize-y font-mono text-xs leading-5"
                  :placeholder="providerYamlExample"
              />
              <Button
                  type="button"
                  variant="outline"
                  size="icon-sm"
                  class="absolute right-2 top-2"
                  @click="copyYamlExample"
              >
                <Check v-if="didCopyExample" class="size-4"/>
                <Copy v-else class="size-4"/>
                <span class="sr-only">Use example</span>
              </Button>
            </div>

            <div class="flex justify-end gap-2">
              <Button type="button" variant="outline" size="sm" @click="copyYamlExample">
                <Copy class="size-4"/>
                Use example
              </Button>
              <Button type="submit" size="sm" :disabled="isImporting">
                <Loader2 v-if="isImporting" class="size-4 animate-spin"/>
                <Upload v-else class="size-4"/>
                Import YAML
              </Button>
            </div>
          </form>
        </TabsContent>
      </Tabs>
    </div>

    <Sheet :open="isConnectionOpen" @update:open="isConnectionOpen = $event">
      <SheetContent class="w-full overflow-y-auto sm:max-w-2xl">
        <form class="flex min-h-full flex-col" @submit.prevent="submitConnection">
          <SheetHeader>
            <SheetTitle>New Provider Connection</SheetTitle>
            <SheetDescription>Configure a tenant connection for the selected provider.</SheetDescription>
          </SheetHeader>

          <div class="grid gap-5 px-4">
            <Alert v-if="connectionDisplayError" variant="destructive">
              <AlertDescription>{{ connectionDisplayError }}</AlertDescription>
            </Alert>

            <div class="grid gap-2">
              <Label>Provider</Label>
              <Select
                  :model-value="connectionForm.provider_connector_id"
                  @update:model-value="connectionForm.provider_connector_id = String($event)"
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select provider"/>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                      v-for="connector in connectors"
                      :key="connector.provider_connector_id"
                      :value="connector.provider_connector_id"
                  >
                    {{ connector.provider_name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <div class="grid gap-2">
                <Label for="connection-code">Code</Label>
                <Input id="connection-code" v-model="connectionForm.connection_code"/>
              </div>
              <div class="grid gap-2">
                <Label for="connection-name">Name</Label>
                <Input id="connection-name" v-model="connectionForm.connection_name"/>
              </div>
              <div class="grid gap-2">
                <Label>Channel</Label>
                <Select
                    :model-value="connectionForm.channel_code"
                    @update:model-value="connectionForm.channel_code = String($event)"
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select channel"/>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="channel in selectedConnector?.channels ?? []" :key="channel" :value="channel">
                      {{ formatChannel(channel) }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div v-if="selectedMessageTypes.length > 0" class="rounded-lg border p-3 text-sm">
              <div class="mb-2 text-xs font-semibold text-muted-foreground">Message types</div>
              <div class="flex flex-wrap gap-2">
                <span
                    v-for="type in selectedMessageTypes"
                    :key="type.provider_message_type_id"
                    class="rounded border bg-muted px-2 py-1 text-xs"
                >
                  {{ formatChannel(type.channel_code) }} · {{ type.message_type_code }}
                </span>
              </div>
            </div>

            <div v-if="selectedConfigFields.length > 0" class="grid gap-3">
              <h3 class="text-sm font-semibold">Config</h3>
              <div v-for="field in selectedConfigFields" :key="field.key" class="grid gap-2">
                <div v-if="field.type === 'boolean'" class="flex items-center gap-2 rounded-md border p-3">
                  <Checkbox
                      :id="`config-${field.key}`"
                      :model-value="booleanSchemaValue(configValues, field.key)"
                      @update:model-value="updateConfigBoolean(field.key, $event)"
                  />
                  <Label :for="`config-${field.key}`">
                    {{ field.label }}<span v-if="field.required" class="text-destructive"> *</span>
                  </Label>
                </div>
                <template v-else>
                  <Label :for="`config-${field.key}`">
                    {{ field.label }}<span v-if="field.required" class="text-destructive"> *</span>
                  </Label>
                  <Input
                      :id="`config-${field.key}`"
                      :model-value="stringSchemaValue(configValues, field.key)"
                      :type="schemaInputType(field)"
                      @update:model-value="updateConfigValue(field.key, $event)"
                  />
                </template>
              </div>
            </div>

            <div v-if="selectedSecretFields.length > 0" class="grid gap-3">
              <h3 class="text-sm font-semibold">Secrets</h3>
              <div v-for="field in selectedSecretFields" :key="field.key" class="grid gap-2">
                <div v-if="field.type === 'boolean'" class="flex items-center gap-2 rounded-md border p-3">
                  <Checkbox
                      :id="`secret-${field.key}`"
                      :model-value="booleanSchemaValue(secretValues, field.key)"
                      @update:model-value="updateSecretBoolean(field.key, $event)"
                  />
                  <Label :for="`secret-${field.key}`">
                    {{ field.label }}<span v-if="field.required" class="text-destructive"> *</span>
                  </Label>
                </div>
                <template v-else>
                  <Label :for="`secret-${field.key}`">
                    {{ field.label }}<span v-if="field.required" class="text-destructive"> *</span>
                  </Label>
                  <Input
                      :id="`secret-${field.key}`"
                      :model-value="stringSchemaValue(secretValues, field.key)"
                      :type="schemaInputType(field)"
                      @update:model-value="updateSecretValue(field.key, $event)"
                  />
                </template>
              </div>
            </div>
          </div>

          <SheetFooter class="sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" @click="isConnectionOpen = false">Cancel</Button>
            <Button type="submit" :disabled="isCreatingConnection">
              <Loader2 v-if="isCreatingConnection" class="size-4 animate-spin"/>
              <KeyRound v-else class="size-4"/>
              Create
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  </SettingsLayout>
</template>
