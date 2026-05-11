<script setup lang="ts">
import {computed, onMounted, reactive, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {KeyRound, Loader2, Plus, RefreshCcw, Upload} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {
  communicationApi,
  type ProviderConnection,
  type ProviderConnector,
  type ProviderMessageType
} from "@/api/communication";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {Alert, AlertDescription} from "@/components/ui/alert";
import {Button} from "@/components/ui/button";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle} from "@/components/ui/sheet";
import {Textarea} from "@/components/ui/textarea";
import {SettingsLayout} from "@/layouts";
import {coerceSchemaValues, initialSchemaForm, schemaFields} from "./schemaForm";

const router = useRouter();
const sessionStore = useSessionStore();

const connectors = ref<ProviderConnector[]>([]);
const messageTypes = ref<ProviderMessageType[]>([]);
const connections = ref<ProviderConnection[]>([]);
const isLoading = ref(false);
const pageError = ref<string | null>(null);

const isImportOpen = ref(false);
const yamlContent = ref("");
const isImporting = ref(false);
const importError = ref<string | null>(null);

const isConnectionOpen = ref(false);
const isCreatingConnection = ref(false);
const connectionError = ref<string | null>(null);
const connectionForm = reactive({
  provider_connector_id: "",
  connection_code: "",
  connection_name: "",
  channel_code: ""
});
const configValues = ref<Record<string, string>>({});
const secretValues = ref<Record<string, string>>({});

const selectedConnector = computed(() => (
    connectors.value.find((connector) => connector.provider_connector_id === connectionForm.provider_connector_id) ?? null
));
const selectedMessageTypes = computed(() => messageTypes.value.filter((type) => (
    type.provider_connector_id === selectedConnector.value?.provider_connector_id
)));

onMounted(() => {
  void loadData();
});

watch(selectedConnector, (connector) => {
  configValues.value = initialSchemaForm(connector?.config_schema);
  secretValues.value = initialSchemaForm(connector?.secrets_schema);
  connectionForm.channel_code = connector?.channels[0] ?? "";
}, {immediate: false});

async function loadData() {
  isLoading.value = true;
  pageError.value = null;

  try {
    const [providerResult, connectionResult] = await Promise.all([
      communicationApi.listProviderConnectors(),
      communicationApi.listProviderConnections()
    ]);
    connectors.value = providerResult.connectors;
    messageTypes.value = providerResult.message_types;
    connections.value = connectionResult.items;
  } catch (error) {
    await handleApiFailure(error, "Could not load providers.");
  } finally {
    isLoading.value = false;
  }
}

function openImportSheet() {
  yamlContent.value = "";
  importError.value = null;
  isImportOpen.value = true;
}

function openConnectionSheet(connector?: ProviderConnector) {
  connectionError.value = null;
  const target = connector ?? connectors.value[0] ?? null;
  connectionForm.provider_connector_id = target?.provider_connector_id ?? "";
  connectionForm.connection_code = target ? `${target.provider_code}_${target.channels[0]?.toLowerCase() ?? "main"}` : "";
  connectionForm.connection_name = target ? `${target.provider_name} ${target.channels[0] ?? ""}`.trim() : "";
  connectionForm.channel_code = target?.channels[0] ?? "";
  configValues.value = initialSchemaForm(target?.config_schema);
  secretValues.value = initialSchemaForm(target?.secrets_schema);
  isConnectionOpen.value = true;
}

async function submitImport() {
  importError.value = null;
  isImporting.value = true;

  try {
    await communicationApi.importConnectorYaml(yamlContent.value);
    isImportOpen.value = false;
    await loadData();
  } catch (error) {
    importError.value = getApiErrorMessage(error, "Could not import provider YAML.");
  } finally {
    isImporting.value = false;
  }
}

async function submitConnection() {
  if (!selectedConnector.value) {
    connectionError.value = "Provider connector is required.";
    return;
  }

  connectionError.value = null;
  isCreatingConnection.value = true;

  try {
    const created = await communicationApi.createProviderConnection({
      provider_connector_id: connectionForm.provider_connector_id,
      connection_code: connectionForm.connection_code.trim(),
      connection_name: connectionForm.connection_name.trim(),
      channel_code: connectionForm.channel_code,
      config: coerceSchemaValues(selectedConnector.value.config_schema, configValues.value),
      secrets: coerceSchemaValues(selectedConnector.value.secrets_schema, secretValues.value)
    });
    connections.value = [...connections.value, created];
    isConnectionOpen.value = false;
  } catch (error) {
    connectionError.value = getApiErrorMessage(error, "Could not create provider connection.");
  } finally {
    isCreatingConnection.value = false;
  }
}

function connectorName(providerConnectorId: string): string {
  return connectors.value.find((connector) => connector.provider_connector_id === providerConnectorId)?.provider_name ?? "Provider";
}

function messageTypeCount(connector: ProviderConnector): number {
  return messageTypes.value.filter((type) => type.provider_connector_id === connector.provider_connector_id).length;
}

async function handleApiFailure(error: unknown, fallback: string) {
  if (getApiErrorStatus(error) === 401) {
    sessionStore.clearSession();
    await router.push("/login");
    return;
  }

  pageError.value = getApiErrorMessage(error, fallback);
}
</script>

<template>
  <SettingsLayout
      title="Communication Providers"
      active-item="communication-providers"
      :breadcrumbs="[{label: 'Workspace'}, {label: 'Communication'}, {label: 'Providers'}]"
  >
    <div class="flex min-h-[560px] flex-col">
      <header class="flex items-start justify-between gap-4">
        <div class="grid gap-1">
          <h1 class="text-base font-semibold">Providers</h1>
          <p class="text-sm text-muted-foreground">Connector contracts and tenant connections</p>
        </div>
        <div class="flex items-center gap-2">
          <Button type="button" variant="outline" size="sm" @click="loadData">
            <RefreshCcw class="size-4"/>
            Refresh
          </Button>
          <Button type="button" variant="outline" size="sm" @click="openImportSheet">
            <Upload class="size-4"/>
            Import YAML
          </Button>
          <Button type="button" size="sm" :disabled="connectors.length === 0" @click="openConnectionSheet()">
            <Plus class="size-4"/>
            New Connection
          </Button>
        </div>
      </header>

      <Alert v-if="pageError" class="mt-5" variant="destructive">
        <AlertDescription>{{ pageError }}</AlertDescription>
      </Alert>

      <div class="mt-6 grid gap-6 xl:grid-cols-[1fr_1fr]">
        <section class="min-w-0">
          <h2 class="mb-3 text-sm font-semibold">Connector definitions</h2>
          <div class="overflow-hidden rounded-md border">
            <table class="w-full border-collapse text-left text-sm">
              <thead class="bg-background text-xs font-semibold text-muted-foreground">
              <tr class="border-b">
                <th class="px-3 py-2">Provider</th>
                <th class="px-3 py-2">Channels</th>
                <th class="w-24 px-3 py-2 text-right">Types</th>
                <th class="w-28 px-3 py-2"/>
              </tr>
              </thead>
              <tbody>
              <tr v-if="isLoading">
                <td colspan="4" class="px-3 py-10 text-center text-muted-foreground">
                  <span class="inline-flex items-center gap-2">
                    <Loader2 class="size-4 animate-spin"/>
                    Loading providers...
                  </span>
                </td>
              </tr>
              <tr v-else-if="connectors.length === 0">
                <td colspan="4" class="px-3 py-10 text-center text-muted-foreground">No providers imported.</td>
              </tr>
              <tr v-for="connector in connectors" v-else :key="connector.provider_connector_id"
                  class="border-b last:border-b-0">
                <td class="px-3 py-2">
                  <div class="font-medium">{{ connector.provider_name }}</div>
                  <div class="text-xs text-muted-foreground">{{ connector.provider_code }} · {{
                      connector.version
                    }}
                  </div>
                </td>
                <td class="px-3 py-2 text-muted-foreground">{{ connector.channels.join(", ") }}</td>
                <td class="px-3 py-2 text-right text-muted-foreground">{{ messageTypeCount(connector) }}</td>
                <td class="px-3 py-2 text-right">
                  <Button type="button" variant="ghost" size="sm" @click="openConnectionSheet(connector)">
                    <KeyRound class="size-4"/>
                    Connect
                  </Button>
                </td>
              </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="min-w-0">
          <h2 class="mb-3 text-sm font-semibold">Connections</h2>
          <div class="overflow-hidden rounded-md border">
            <table class="w-full border-collapse text-left text-sm">
              <thead class="bg-background text-xs font-semibold text-muted-foreground">
              <tr class="border-b">
                <th class="px-3 py-2">Name</th>
                <th class="px-3 py-2">Provider</th>
                <th class="px-3 py-2">Channel</th>
                <th class="px-3 py-2">Secrets</th>
              </tr>
              </thead>
              <tbody>
              <tr v-if="connections.length === 0">
                <td colspan="4" class="px-3 py-10 text-center text-muted-foreground">No connections.</td>
              </tr>
              <tr v-for="connection in connections" v-else :key="connection.provider_connection_id"
                  class="border-b last:border-b-0">
                <td class="px-3 py-2">
                  <div class="font-medium">{{ connection.connection_name }}</div>
                  <div class="text-xs text-muted-foreground">{{ connection.connection_code }}</div>
                </td>
                <td class="px-3 py-2 text-muted-foreground">{{ connectorName(connection.provider_connector_id) }}</td>
                <td class="px-3 py-2 text-muted-foreground">{{ connection.channel_code }}</td>
                <td class="px-3 py-2 text-muted-foreground">{{ connection.has_secrets ? "Stored" : "Empty" }}</td>
              </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>

    <Sheet :open="isImportOpen" @update:open="isImportOpen = $event">
      <SheetContent class="w-full overflow-y-auto sm:max-w-2xl">
        <form class="flex min-h-full flex-col" @submit.prevent="submitImport">
          <SheetHeader>
            <SheetTitle>Import Provider YAML</SheetTitle>
          </SheetHeader>
          <div class="grid gap-4 px-4">
            <Alert v-if="importError" variant="destructive">
              <AlertDescription>{{ importError }}</AlertDescription>
            </Alert>
            <Textarea v-model="yamlContent" class="min-h-96 font-mono text-xs" placeholder="provider_code: gms"/>
          </div>
          <SheetFooter class="sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" @click="isImportOpen = false">Cancel</Button>
            <Button type="submit" :disabled="isImporting || !yamlContent.trim()">
              <Loader2 v-if="isImporting" class="size-4 animate-spin"/>
              Import
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>

    <Sheet :open="isConnectionOpen" @update:open="isConnectionOpen = $event">
      <SheetContent class="w-full overflow-y-auto sm:max-w-2xl">
        <form class="flex min-h-full flex-col" @submit.prevent="submitConnection">
          <SheetHeader>
            <SheetTitle>New Provider Connection</SheetTitle>
          </SheetHeader>

          <div class="grid gap-5 px-4">
            <Alert v-if="connectionError" variant="destructive">
              <AlertDescription>{{ connectionError }}</AlertDescription>
            </Alert>

            <div class="grid gap-2">
              <Label>Provider</Label>
              <Select :model-value="connectionForm.provider_connector_id"
                      @update:model-value="connectionForm.provider_connector_id = String($event)">
                <SelectTrigger>
                  <SelectValue placeholder="Select provider"/>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="connector in connectors" :key="connector.provider_connector_id"
                              :value="connector.provider_connector_id">
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
                <Select :model-value="connectionForm.channel_code"
                        @update:model-value="connectionForm.channel_code = String($event)">
                  <SelectTrigger>
                    <SelectValue placeholder="Select channel"/>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="channel in selectedConnector?.channels ?? []" :key="channel" :value="channel">
                      {{ channel }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div v-if="selectedMessageTypes.length > 0" class="rounded-md border p-3 text-sm">
              <div class="mb-2 text-xs font-semibold text-muted-foreground">Message types</div>
              <div class="flex flex-wrap gap-2">
                <span v-for="type in selectedMessageTypes" :key="type.provider_message_type_id"
                      class="rounded bg-muted px-2 py-1 text-xs">
                  {{ type.channel_code }} · {{ type.message_type_code }}
                </span>
              </div>
            </div>

            <div v-if="schemaFields(selectedConnector?.config_schema).length > 0" class="grid gap-3">
              <h3 class="text-sm font-semibold">Config</h3>
              <div v-for="field in schemaFields(selectedConnector?.config_schema)" :key="field.key" class="grid gap-2">
                <Label :for="`config-${field.key}`">{{ field.label }}</Label>
                <Input :id="`config-${field.key}`" v-model="configValues[field.key]"
                       :type="field.type === 'integer' ? 'number' : 'text'"/>
              </div>
            </div>

            <div v-if="schemaFields(selectedConnector?.secrets_schema).length > 0" class="grid gap-3">
              <h3 class="text-sm font-semibold">Secrets</h3>
              <div v-for="field in schemaFields(selectedConnector?.secrets_schema)" :key="field.key" class="grid gap-2">
                <Label :for="`secret-${field.key}`">{{ field.label }}</Label>
                <Input :id="`secret-${field.key}`" v-model="secretValues[field.key]"
                       :type="field.type === 'password' ? 'password' : 'text'"/>
              </div>
            </div>
          </div>

          <SheetFooter class="sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" @click="isConnectionOpen = false">Cancel</Button>
            <Button type="submit" :disabled="isCreatingConnection">
              <Loader2 v-if="isCreatingConnection" class="size-4 animate-spin"/>
              Create
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  </SettingsLayout>
</template>
