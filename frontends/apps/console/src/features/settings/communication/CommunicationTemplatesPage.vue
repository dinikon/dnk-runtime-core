<script setup lang="ts">
import {computed, onMounted, reactive, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {Loader2, Plus, RefreshCcw, Send} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {
  communicationApi,
  type MessageTemplate,
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
import {coerceSchemaValues, initialSchemaForm, parseJsonObject, schemaFields} from "./schemaForm";

const MESSAGE_CLASSES = ["MARKETING", "TRANSACTIONAL", "SERVICE", "OTP", "INFO"];

const router = useRouter();
const sessionStore = useSessionStore();

const connectors = ref<ProviderConnector[]>([]);
const messageTypes = ref<ProviderMessageType[]>([]);
const templates = ref<MessageTemplate[]>([]);
const isLoading = ref(false);
const pageError = ref<string | null>(null);
const pageNotice = ref<string | null>(null);

const isTemplateOpen = ref(false);
const isCreatingTemplate = ref(false);
const templateError = ref<string | null>(null);
const templateForm = reactive({
  template_code: "",
  name: "",
  description: "",
  provider_connector_id: "",
  provider_message_type_id: "",
  message_class: "TRANSACTIONAL"
});
const payloadValues = ref<Record<string, string>>({});
const variablesSchemaText = ref("{\n  \"type\": \"object\",\n  \"additionalProperties\": true\n}");

const isSendOpen = ref(false);
const isSending = ref(false);
const sendError = ref<string | null>(null);
const sendForm = reactive({
  template_id: "",
  recipient_address: "",
  variables: "{}"
});

const selectedConnector = computed(() => (
    connectors.value.find((connector) => connector.provider_connector_id === templateForm.provider_connector_id) ?? null
));
const availableMessageTypes = computed(() => messageTypes.value.filter((type) => (
    type.provider_connector_id === templateForm.provider_connector_id
)));
const selectedMessageType = computed(() => (
    messageTypes.value.find((type) => type.provider_message_type_id === templateForm.provider_message_type_id) ?? null
));

onMounted(() => {
  void loadData();
});

watch(selectedConnector, () => {
  const firstType = availableMessageTypes.value[0] ?? null;
  templateForm.provider_message_type_id = firstType?.provider_message_type_id ?? "";
});

watch(selectedMessageType, (messageType) => {
  payloadValues.value = initialSchemaForm(messageType?.field_schema);
});

async function loadData() {
  isLoading.value = true;
  pageError.value = null;

  try {
    const [providerResult, templateResult] = await Promise.all([
      communicationApi.listProviderConnectors(),
      communicationApi.listTemplates()
    ]);
    connectors.value = providerResult.connectors;
    messageTypes.value = providerResult.message_types;
    templates.value = templateResult.items;
  } catch (error) {
    await handleApiFailure(error, "Could not load templates.");
  } finally {
    isLoading.value = false;
  }
}

function openTemplateSheet() {
  templateError.value = null;
  const connector = connectors.value[0] ?? null;
  const messageType = messageTypes.value.find((type) => type.provider_connector_id === connector?.provider_connector_id) ?? null;
  templateForm.template_code = "";
  templateForm.name = "";
  templateForm.description = "";
  templateForm.provider_connector_id = connector?.provider_connector_id ?? "";
  templateForm.provider_message_type_id = messageType?.provider_message_type_id ?? "";
  templateForm.message_class = "TRANSACTIONAL";
  payloadValues.value = initialSchemaForm(messageType?.field_schema);
  variablesSchemaText.value = "{\n  \"type\": \"object\",\n  \"additionalProperties\": true\n}";
  isTemplateOpen.value = true;
}

function openSendSheet(template?: MessageTemplate) {
  sendError.value = null;
  sendForm.template_id = template?.template_id ?? templates.value[0]?.template_id ?? "";
  sendForm.recipient_address = "";
  sendForm.variables = "{}";
  isSendOpen.value = true;
}

function formatVersion(version: string | null) {
  if (!version) {
    return "—";
  }
  return new Date(version).toISOString().replace(".000Z", "Z");
}

async function submitTemplate() {
  if (!selectedMessageType.value || !selectedConnector.value) {
    templateError.value = "Provider message type is required.";
    return;
  }

  isCreatingTemplate.value = true;
  templateError.value = null;

  try {
    const variablesSchema = parseJsonObject(variablesSchemaText.value, "Variables schema");
    const created = await communicationApi.createTemplate({
      template_code: templateForm.template_code.trim(),
      name: templateForm.name.trim(),
      description: templateForm.description.trim() || null,
      provider_connector_id: selectedConnector.value.provider_connector_id,
      provider_message_type_id: selectedMessageType.value.provider_message_type_id,
      channel_code: selectedMessageType.value.channel_code,
      message_class: templateForm.message_class
    });
    const version = await communicationApi.createTemplateVersion(created.template_id, {
      template_payload: coerceSchemaValues(selectedMessageType.value.field_schema, payloadValues.value),
      variables_schema: variablesSchema
    });
    await communicationApi.activateTemplateVersion(created.template_id, version.template_version_id);
    isTemplateOpen.value = false;
    await loadData();
  } catch (error) {
    templateError.value = error instanceof Error
        ? error.message
        : getApiErrorMessage(error, "Could not create template.");
  } finally {
    isCreatingTemplate.value = false;
  }
}

async function submitSend() {
  const template = templates.value.find((item) => item.template_id === sendForm.template_id);
  if (!template) {
    sendError.value = "Template is required.";
    return;
  }

  isSending.value = true;
  sendError.value = null;
  pageNotice.value = null;

  try {
    const result = await communicationApi.sendCommunication({
      initiator_type: "API",
      message_class: template.message_class,
      channel_code: template.channel_code,
      recipient_address: sendForm.recipient_address.trim(),
      template_id: template.template_id,
      variables: parseJsonObject(sendForm.variables, "Variables")
    });
    pageNotice.value = `Queued message ${result.outbound_message_id}.`;
    isSendOpen.value = false;
  } catch (error) {
    sendError.value = error instanceof Error
        ? error.message
        : getApiErrorMessage(error, "Could not send message.");
  } finally {
    isSending.value = false;
  }
}

function providerName(providerConnectorId: string): string {
  return connectors.value.find((connector) => connector.provider_connector_id === providerConnectorId)?.provider_name ?? "Provider";
}

function messageTypeName(providerMessageTypeId: string): string {
  return messageTypes.value.find((type) => type.provider_message_type_id === providerMessageTypeId)?.name ?? "Message type";
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
      title="Communication Templates"
      active-item="communication-templates"
      :breadcrumbs="[{label: 'Workspace'}, {label: 'Communication'}, {label: 'Templates'}]"
  >
    <div class="flex min-h-[560px] flex-col">
      <header class="flex items-start justify-between gap-4">
        <div class="grid gap-1">
          <h1 class="text-base font-semibold">Templates</h1>
          <p class="text-sm text-muted-foreground">Provider-bound message templates and active versions</p>
        </div>
        <div class="flex items-center gap-2">
          <Button type="button" variant="outline" size="sm" @click="loadData">
            <RefreshCcw class="size-4"/>
            Refresh
          </Button>
          <Button type="button" variant="outline" size="sm" :disabled="templates.length === 0" @click="openSendSheet()">
            <Send class="size-4"/>
            Test Send
          </Button>
          <Button type="button" size="sm" :disabled="messageTypes.length === 0" @click="openTemplateSheet">
            <Plus class="size-4"/>
            New Template
          </Button>
        </div>
      </header>

      <Alert v-if="pageError" class="mt-5" variant="destructive">
        <AlertDescription>{{ pageError }}</AlertDescription>
      </Alert>
      <Alert v-if="pageNotice" class="mt-5">
        <AlertDescription>{{ pageNotice }}</AlertDescription>
      </Alert>

      <div class="mt-6 overflow-hidden rounded-md border">
        <table class="w-full border-collapse text-left text-sm">
          <thead class="bg-background text-xs font-semibold text-muted-foreground">
          <tr class="border-b">
            <th class="px-3 py-2">Template</th>
            <th class="px-3 py-2">Provider</th>
            <th class="px-3 py-2">Type</th>
            <th class="px-3 py-2">Status</th>
            <th class="w-28 px-3 py-2"/>
          </tr>
          </thead>
          <tbody>
          <tr v-if="isLoading">
            <td colspan="5" class="px-3 py-10 text-center text-muted-foreground">
              <span class="inline-flex items-center gap-2">
                <Loader2 class="size-4 animate-spin"/>
                Loading templates...
              </span>
            </td>
          </tr>
          <tr v-else-if="templates.length === 0">
            <td colspan="5" class="px-3 py-10 text-center text-muted-foreground">No templates.</td>
          </tr>
          <tr v-for="template in templates" v-else :key="template.template_id" class="border-b last:border-b-0">
            <td class="px-3 py-2">
              <div class="font-medium">{{ template.name }}</div>
              <div class="text-xs text-muted-foreground">{{ template.template_code }}</div>
            </td>
            <td class="px-3 py-2 text-muted-foreground">{{ providerName(template.provider_connector_id) }}</td>
            <td class="px-3 py-2 text-muted-foreground">{{ template.channel_code }} ·
              {{ messageTypeName(template.provider_message_type_id) }}
            </td>
            <td class="px-3 py-2 text-muted-foreground">{{ template.status }} v{{
                formatVersion(template.active_version)
              }}
            </td>
            <td class="px-3 py-2 text-right">
              <Button type="button" variant="ghost" size="sm" @click="openSendSheet(template)">
                <Send class="size-4"/>
                Send
              </Button>
            </td>
          </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Sheet :open="isTemplateOpen" @update:open="isTemplateOpen = $event">
      <SheetContent class="w-full overflow-y-auto sm:max-w-2xl">
        <form class="flex min-h-full flex-col" @submit.prevent="submitTemplate">
          <SheetHeader>
            <SheetTitle>New Template</SheetTitle>
          </SheetHeader>

          <div class="grid gap-5 px-4">
            <Alert v-if="templateError" variant="destructive">
              <AlertDescription>{{ templateError }}</AlertDescription>
            </Alert>

            <div class="grid gap-4 md:grid-cols-2">
              <div class="grid gap-2">
                <Label for="template-code">Code</Label>
                <Input id="template-code" v-model="templateForm.template_code" placeholder="loan_approved_viber"/>
              </div>
              <div class="grid gap-2">
                <Label for="template-name">Name</Label>
                <Input id="template-name" v-model="templateForm.name"/>
              </div>
            </div>

            <div class="grid gap-2">
              <Label for="template-description">Description</Label>
              <Textarea id="template-description" v-model="templateForm.description" placeholder="Optional"/>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <div class="grid gap-2">
                <Label>Provider</Label>
                <Select :model-value="templateForm.provider_connector_id"
                        @update:model-value="templateForm.provider_connector_id = String($event)">
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
              <div class="grid gap-2">
                <Label>Message type</Label>
                <Select :model-value="templateForm.provider_message_type_id"
                        @update:model-value="templateForm.provider_message_type_id = String($event)">
                  <SelectTrigger>
                    <SelectValue placeholder="Select type"/>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="type in availableMessageTypes" :key="type.provider_message_type_id"
                                :value="type.provider_message_type_id">
                      {{ type.channel_code }} · {{ type.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="grid gap-2">
                <Label>Class</Label>
                <Select :model-value="templateForm.message_class"
                        @update:model-value="templateForm.message_class = String($event)">
                  <SelectTrigger>
                    <SelectValue placeholder="Select class"/>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="messageClass in MESSAGE_CLASSES" :key="messageClass" :value="messageClass">
                      {{ messageClass }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div v-if="schemaFields(selectedMessageType?.field_schema).length > 0" class="grid gap-3">
              <h3 class="text-sm font-semibold">Template payload</h3>
              <div v-for="field in schemaFields(selectedMessageType?.field_schema)" :key="field.key" class="grid gap-2">
                <Label :for="`payload-${field.key}`">{{ field.label }}</Label>
                <Textarea v-if="field.key === 'text'" :id="`payload-${field.key}`" v-model="payloadValues[field.key]"
                          class="min-h-24"/>
                <Input v-else :id="`payload-${field.key}`" v-model="payloadValues[field.key]"
                       :type="field.type === 'integer' ? 'number' : 'text'"/>
              </div>
            </div>

            <div class="grid gap-2">
              <Label for="variables-schema">Variables schema</Label>
              <Textarea id="variables-schema" v-model="variablesSchemaText" class="min-h-40 font-mono text-xs"/>
            </div>
          </div>

          <SheetFooter class="sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" @click="isTemplateOpen = false">Cancel</Button>
            <Button type="submit" :disabled="isCreatingTemplate">
              <Loader2 v-if="isCreatingTemplate" class="size-4 animate-spin"/>
              Create
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>

    <Sheet :open="isSendOpen" @update:open="isSendOpen = $event">
      <SheetContent class="w-full overflow-y-auto sm:max-w-xl">
        <form class="flex min-h-full flex-col" @submit.prevent="submitSend">
          <SheetHeader>
            <SheetTitle>Test Send</SheetTitle>
          </SheetHeader>

          <div class="grid gap-5 px-4">
            <Alert v-if="sendError" variant="destructive">
              <AlertDescription>{{ sendError }}</AlertDescription>
            </Alert>

            <div class="grid gap-2">
              <Label>Template</Label>
              <Select :model-value="sendForm.template_id" @update:model-value="sendForm.template_id = String($event)">
                <SelectTrigger>
                  <SelectValue placeholder="Select template"/>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="template in templates" :key="template.template_id" :value="template.template_id">
                    {{ template.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="grid gap-2">
              <Label for="recipient-address">Recipient</Label>
              <Input id="recipient-address" v-model="sendForm.recipient_address" placeholder="380671112233"/>
            </div>

            <div class="grid gap-2">
              <Label for="send-variables">Variables</Label>
              <Textarea id="send-variables" v-model="sendForm.variables" class="min-h-40 font-mono text-xs"/>
            </div>
          </div>

          <SheetFooter class="sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" @click="isSendOpen = false">Cancel</Button>
            <Button type="submit" :disabled="isSending">
              <Loader2 v-if="isSending" class="size-4 animate-spin"/>
              Queue
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  </SettingsLayout>
</template>
