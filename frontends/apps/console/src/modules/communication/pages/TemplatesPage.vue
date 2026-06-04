<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { RefreshCcw, Save, SendHorizontal } from "lucide-vue-next";
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
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";
import JsonSchemaForm from "@/modules/communication/components/JsonSchemaForm.vue";
import StatusBadge from "@/modules/communication/components/StatusBadge.vue";
import {
  apiErrorMessage,
  buildJsonSchemaDefaults,
  createClientUuid,
  formatJsonObject,
  parseJsonObject,
} from "@/modules/communication/lib";

const MESSAGE_CLASSES = [
  "TRANSACTIONAL",
  "MARKETING",
  "SERVICE",
  "OTP",
  "INFO",
];

const queryClient = useQueryClient();

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

const selectedTemplateId = ref("");
const recipientIdentifierType = ref("phone");
const recipientAddress = ref("");
const recipientSnapshotText = ref(formatJsonObject({}));
const variablesText = ref(formatJsonObject({}));
const priority = ref(100);

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

const templatesQuery = useQuery({
  queryKey: ["communication", "message-templates"],
  queryFn: communicationApi.listMessageTemplates,
  retry: false,
});

const createTemplateMutation = useMutation({
  mutationFn: communicationApi.createMessageTemplate,
});

const createVersionMutation = useMutation({
  mutationFn: ({
    templateId,
    payload,
  }: {
    templateId: string;
    payload: {
      template_payload: JsonObject;
      variables_schema: JsonObject;
    };
  }) => communicationApi.createTemplateVersion(templateId, payload),
});

const activateVersionMutation = useMutation({
  mutationFn: ({
    templateId,
    versionId,
  }: {
    templateId: string;
    versionId: string;
  }) => communicationApi.activateTemplateVersion(templateId, versionId),
});

const sendMutation = useMutation({
  mutationFn: communicationApi.sendCommunication,
});

const connectors = computed(() => catalogQuery.data.value?.connectors ?? []);
const messageTypes = computed(
  () => catalogQuery.data.value?.message_types ?? [],
);
const connections = computed(() => connectionsQuery.data.value?.items ?? []);
const templates = computed(() => templatesQuery.data.value?.items ?? []);
const selectedConnection = computed(() =>
  connections.value.find(
    (connection) =>
      connection.provider_connection_id === selectedConnectionId.value,
  ),
);
const selectedConnector = computed(() =>
  connectors.value.find(
    (connector) =>
      connector.provider_connector_id ===
      selectedConnection.value?.provider_connector_id,
  ),
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
const templatesForConnection = computed(() =>
  templates.value.filter(
    (template) =>
      template.provider_connector_id ===
        selectedConnection.value?.provider_connector_id &&
      template.channel_code === selectedConnection.value?.channel_code,
  ),
);
const selectedTemplate = computed(() =>
  templates.value.find(
    (template) => template.template_id === selectedTemplateId.value,
  ),
);
const isCreatingTemplate = computed(
  () =>
    createTemplateMutation.isPending.value ||
    createVersionMutation.isPending.value ||
    activateVersionMutation.isPending.value,
);

watch(
  connections,
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

watch(
  templates,
  (items) => {
    if (!items.length) {
      selectedTemplateId.value = "";
      return;
    }

    if (
      !selectedTemplateId.value ||
      !items.some((item) => item.template_id === selectedTemplateId.value)
    ) {
      selectedTemplateId.value =
        items.find((item) => item.active_version_id)?.template_id ??
        items[0].template_id;
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

async function refreshTemplates() {
  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: ["communication", "provider-catalog"],
    }),
    queryClient.invalidateQueries({
      queryKey: ["communication", "provider-connections"],
    }),
    queryClient.invalidateQueries({
      queryKey: ["communication", "message-templates"],
    }),
  ]);
}

async function createTemplateWithActiveVersion() {
  const connection = selectedConnection.value;
  const messageType = selectedMessageType.value;

  if (!connection || !messageType) {
    toast.error("Select a connect and message type.");
    return;
  }

  try {
    const variablesSchema = parseJsonObject(variablesSchemaText.value, {});
    const template = await createTemplateMutation.mutateAsync({
      template_code: templateCode.value.trim(),
      name: templateName.value.trim(),
      description: templateDescription.value.trim() || null,
      provider_connector_id: connection.provider_connector_id,
      provider_message_type_id: messageType.provider_message_type_id,
      channel_code: connection.channel_code,
      message_class: messageClass.value,
    });
    const version = await createVersionMutation.mutateAsync({
      templateId: template.template_id,
      payload: {
        template_payload: templatePayload.value,
        variables_schema: variablesSchema,
      },
    });

    await activateVersionMutation.mutateAsync({
      templateId: template.template_id,
      versionId: version.template_version_id,
    });

    selectedTemplateId.value = template.template_id;
    toast.success("Template created and activated.");
    await refreshTemplates();
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

async function sendTestMessage() {
  const template = selectedTemplate.value;

  if (!template) {
    toast.error("Select a template.");
    return;
  }

  try {
    const recipientSnapshot = parseJsonObject(recipientSnapshotText.value, {});
    const variables = parseJsonObject(variablesText.value, {});

    const result = await sendMutation.mutateAsync({
      initiator_type: "CONSOLE_TEST",
      initiator_ref_id: "communication-templates",
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
      priority: priority.value,
    });

    toast.success(`Test message queued: ${result.internal_status}.`);
  } catch (error) {
    toast.error(apiErrorMessage(error));
  }
}

function connectorName(connectorId: string) {
  return (
    connectors.value.find(
      (connector) => connector.provider_connector_id === connectorId,
    )?.provider_name ?? "Provider"
  );
}

function messageTypeName(messageTypeId: string) {
  return (
    messageTypes.value.find(
      (messageType) => messageType.provider_message_type_id === messageTypeId,
    )?.name ?? "Message type"
  );
}

function formatDate(value: string | null) {
  if (!value) {
    return "No active version";
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
        description="Create provider-bound message templates, activate payload versions, and queue quick single-recipient tests."
      />
      <Button
        type="button"
        variant="outline"
        :disabled="
          catalogQuery.isFetching.value ||
          connectionsQuery.isFetching.value ||
          templatesQuery.isFetching.value
        "
        @click="refreshTemplates"
      >
        <RefreshCcw
          class="size-4"
          :class="{
            'animate-spin':
              catalogQuery.isFetching.value ||
              connectionsQuery.isFetching.value ||
              templatesQuery.isFetching.value,
          }"
        />
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

    <div
      class="grid min-h-0 flex-1 gap-4 overflow-hidden xl:grid-cols-[0.95fr_1.05fr]"
    >
      <div class="min-h-0 overflow-auto pr-1">
        <form
          class="grid gap-4 rounded-lg border p-4"
          @submit.prevent="createTemplateWithActiveVersion"
        >
          <div class="grid gap-1">
            <h3 class="text-sm font-semibold">New template</h3>
            <p class="text-sm text-muted-foreground">
              Template fields are generated from the selected provider message
              type.
            </p>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="connect">Connect</label>
            <select
              id="connect"
              v-model="selectedConnectionId"
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="connection in connections"
                :key="connection.provider_connection_id"
                :value="connection.provider_connection_id"
              >
                {{ connection.connection_name }} · {{ connection.channel_code }}
              </option>
            </select>
            <p v-if="selectedConnector" class="text-xs text-muted-foreground">
              {{ selectedConnector.provider_name }}
            </p>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="message-type">
              Message type
            </label>
            <select
              id="message-type"
              v-model="selectedMessageTypeId"
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
          </div>

          <div class="grid gap-3 md:grid-cols-2">
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
            <label class="text-sm font-medium" for="message-class">
              Message class
            </label>
            <select
              id="message-class"
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
              class="min-h-20"
            />
          </div>

          <div class="grid gap-2">
            <h4 class="text-sm font-medium">Payload</h4>
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
              class="min-h-32 font-mono text-xs"
            />
          </div>

          <Button
            type="submit"
            :disabled="
              !selectedConnection || !selectedMessageType || isCreatingTemplate
            "
          >
            <Save class="size-4" />
            {{ isCreatingTemplate ? "Saving" : "Create template" }}
          </Button>
        </form>
      </div>

      <div class="flex min-h-0 flex-col gap-4 overflow-auto pl-1">
        <div class="grid gap-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold">Templates</h3>
            <Badge variant="outline">{{ templates.length }} templates</Badge>
          </div>
          <div class="grid gap-3 md:grid-cols-2">
            <Card
              v-for="template in templates"
              :key="template.template_id"
              class="cursor-pointer transition-colors hover:bg-accent/40"
              :class="{
                'border-primary bg-accent/50':
                  selectedTemplateId === template.template_id,
              }"
              @click="selectedTemplateId = template.template_id"
            >
              <CardHeader class="gap-2">
                <div class="flex items-start justify-between gap-3">
                  <div class="grid gap-1">
                    <CardTitle class="text-base">
                      {{ template.name }}
                    </CardTitle>
                    <CardDescription>
                      {{ template.template_code }} · {{ template.channel_code }}
                    </CardDescription>
                  </div>
                  <StatusBadge :status="template.status" />
                </div>
              </CardHeader>
              <CardContent class="grid gap-2 text-sm text-muted-foreground">
                <div class="flex flex-wrap gap-1">
                  <Badge variant="secondary">
                    {{ connectorName(template.provider_connector_id) }}
                  </Badge>
                  <Badge variant="outline">
                    {{ messageTypeName(template.provider_message_type_id) }}
                  </Badge>
                  <Badge variant="outline">{{ template.message_class }}</Badge>
                </div>
                <span
                  >Active version
                  {{ formatDate(template.active_version) }}</span
                >
              </CardContent>
            </Card>
          </div>
          <p
            v-if="!templatesQuery.isLoading.value && templates.length === 0"
            class="text-sm text-muted-foreground"
          >
            No message templates created yet.
          </p>
        </div>

        <form
          class="grid gap-4 rounded-lg border p-4"
          @submit.prevent="sendTestMessage"
        >
          <div class="grid gap-1">
            <h3 class="text-sm font-semibold">Quick test send</h3>
            <p class="text-sm text-muted-foreground">
              Queue one message with recipient data and template variables.
            </p>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="test-template">
              Template
            </label>
            <select
              id="test-template"
              v-model="selectedTemplateId"
              class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option
                v-for="template in templates"
                :key="template.template_id"
                :value="template.template_id"
              >
                {{ template.name }} · {{ template.channel_code }}
              </option>
            </select>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
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
              class="min-h-32 font-mono text-xs"
            />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="recipient-snapshot">
              Recipient snapshot
            </label>
            <Textarea
              id="recipient-snapshot"
              v-model="recipientSnapshotText"
              class="min-h-28 font-mono text-xs"
            />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium" for="priority">Priority</label>
            <Input id="priority" v-model="priority" type="number" />
          </div>

          <Button
            type="submit"
            :disabled="!selectedTemplate || sendMutation.isPending.value"
          >
            <SendHorizontal class="size-4" />
            {{ sendMutation.isPending.value ? "Sending" : "Send test" }}
          </Button>
        </form>

        <div
          v-if="templatesForConnection.length"
          class="grid gap-2 rounded-lg border p-4"
        >
          <h3 class="text-sm font-semibold">Templates for selected connect</h3>
          <div
            v-for="template in templatesForConnection"
            :key="template.template_id"
            class="flex items-center justify-between gap-3 rounded-md border px-3 py-2"
          >
            <div class="grid gap-1">
              <span class="text-sm font-medium">{{ template.name }}</span>
              <span class="text-xs text-muted-foreground">
                {{ template.template_code }} · {{ template.message_class }}
              </span>
            </div>
            <StatusBadge :status="template.status" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
