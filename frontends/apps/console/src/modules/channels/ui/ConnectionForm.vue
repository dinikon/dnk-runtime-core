<script setup lang="ts">
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import type {
  Platform,
  Connection,
  ConnectionReferences,
  ConnectionSettings,
  JsonValue,
} from "../model/channels.types";
import {
  connectionFormValues,
  connectionSettings,
  settingsSignature,
  validateConnectionForm,
} from "../model/connection-form";
import SchemaSettingsFields from "./SchemaSettingsFields.vue";
function setSettings(value: JsonValue | undefined): void {
  if (value && typeof value === "object" && !Array.isArray(value))
    values.settings = value;
}
const props = defineProps<{
  platform: Platform;
  connection: Connection | undefined;
  references: ConnectionReferences;
  revision: number;
  pending: boolean;
  disabled: boolean;
  error: string | null;
  saveSequence: number;
}>();
const emit = defineEmits<{
  submit: [
    input: {
      revision: number;
      settings: ConnectionSettings;
      credentials?: Record<string, string>;
    },
  ];
  dirty: [value: boolean];
}>();
const values = reactive(connectionFormValues(props.platform, props.connection));
const draftRevision = ref(props.revision),
  localError = ref<string | null>(null),
  serverChanged = ref(false);
let baseline = settingsSignature(connectionSettings(values));
const needsCredentials = computed(
  () => !props.connection || values.replaceCredentials,
);
const fields = computed(() =>
  Object.entries(props.platform.credentialsSchema.properties ?? {}),
);
const endpointLocked = computed(
  () =>
    !!props.platform.endpointSchema.const ||
    !!props.connection?.resourceIdentity,
);
watch(
  values,
  () =>
    emit(
      "dirty",
      settingsSignature(connectionSettings(values)) !== baseline ||
        Object.values(values.credentials).some(Boolean),
    ),
  { deep: true },
);
function clearSecrets(): void {
  for (const key of Object.keys(values.credentials))
    values.credentials[key] = "";
  values.replaceCredentials = !props.connection;
}
onBeforeUnmount(clearSecrets);
watch(
  () => props.saveSequence,
  () => {
    clearSecrets();
    draftRevision.value = props.revision;
    baseline = settingsSignature(connectionSettings(values));
    serverChanged.value = false;
  },
);
watch(
  () => props.revision,
  (revision) => {
    if (!props.connection) return;
    const current = settingsSignature({
      endpoint: props.connection.endpoint,
      options: props.connection.settings,
    });
    if (current === baseline) draftRevision.value = revision;
    else serverChanged.value = true;
  },
);
function acceptRevision(): void {
  draftRevision.value = props.revision;
  serverChanged.value = false;
  baseline = props.connection
    ? settingsSignature({
        endpoint: props.connection.endpoint,
        options: props.connection.settings,
      })
    : baseline;
}
function submit(): void {
  if (props.pending || props.disabled || serverChanged.value) return;
  localError.value = validateConnectionForm(
    values,
    props.platform,
    needsCredentials.value,
  );
  if (localError.value) return;
  emit("submit", {
    revision: draftRevision.value,
    settings: connectionSettings(values),
    ...(needsCredentials.value
      ? { credentials: { ...values.credentials } }
      : {}),
  });
}
</script>
<template>
  <form class="flex flex-col gap-6" @submit.prevent="submit">
    <fieldset
      :disabled="pending || disabled"
      class="flex min-w-0 flex-col gap-6"
    >
      <FieldGroup
        ><Field
          ><FieldLabel for="connection-endpoint">{{
            platform.endpointSchema.title ?? "Адрес ресурса"
          }}</FieldLabel
          ><Input
            id="connection-endpoint"
            v-model="values.endpoint"
            type="url"
            required
            :readonly="endpointLocked"
            :maxlength="platform.endpointSchema.maxLength ?? 2048"
            placeholder="https://shop.example"
          /><FieldDescription>{{
            connection?.resourceIdentity
              ? "Источник подтверждён. Для другого магазина создайте новый канал."
              : platform.endpointSchema.description
          }}</FieldDescription></Field
        >
        <SchemaSettingsFields
          :schema="platform.settingsSchema"
          :model-value="values.settings"
          path="connection-settings"
          :references="references"
          @update:model-value="setSettings"
        />
        <FieldDescription>
          Выберите настройки магазина. Автоматический перевод и пересчёт валюты
          не выполняются.
        </FieldDescription>
      </FieldGroup>
      <section class="flex flex-col gap-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 class="font-medium">Данные доступа</h3>
            <p v-if="connection" class="text-muted-foreground text-sm">
              {{
                connection.candidatePresent
                  ? "Новые ключи ожидают проверки"
                  : connection.credentialsPresent
                    ? "Данные доступа сохранены"
                    : "Нет подтверждённых ключей"
              }}
            </p>
          </div>
          <Button
            v-if="connection && !values.replaceCredentials"
            type="button"
            variant="outline"
            size="sm"
            @click="values.replaceCredentials = true"
            >Заменить ключи</Button
          ><Button
            v-if="connection && values.replaceCredentials"
            type="button"
            variant="ghost"
            size="sm"
            @click="clearSecrets"
            >Отменить замену</Button
          >
        </div>
        <FieldGroup v-if="needsCredentials"
          ><Field v-for="[key, schema] in fields" :key="key"
            ><FieldLabel :for="'credential-' + key">{{
              schema.title ?? key
            }}</FieldLabel
            ><Input
              :id="'credential-' + key"
              v-model="values.credentials[key]"
              type="password"
              autocomplete="new-password"
              :required="platform.credentialsSchema.required?.includes(key)"
              :minlength="schema.minLength"
              :maxlength="schema.maxLength"
            /><FieldDescription v-if="schema.description">{{
              schema.description
            }}</FieldDescription></Field
          ></FieldGroup
        >
      </section>
    </fieldset>
    <Alert v-if="serverChanged"
      ><AlertTitle>Настройки изменились на сервере</AlertTitle
      ><AlertDescription
        ><p>
          Актуально: {{ connection?.endpoint }} · параметры подключения
          обновлены. Ваш ввод сохранён.
        </p>
        <fieldset v-if="connection" disabled class="w-full">
          <SchemaSettingsFields
            :schema="platform.settingsSchema"
            :model-value="connection.settings"
            path="connection-current-settings"
            :references="references"
          />
        </fieldset>
        <Button
          type="button"
          variant="outline"
          size="sm"
          @click="acceptRevision"
          >Сверил настройки, продолжить с моим вводом</Button
        ></AlertDescription
      ></Alert
    ><Alert v-if="localError || error" variant="destructive"
      ><AlertDescription>{{ localError ?? error }}</AlertDescription></Alert
    >
    <div class="flex flex-wrap items-center gap-3">
      <Button type="submit" :disabled="pending || disabled || serverChanged">{{
        pending
          ? "Сохраняем…"
          : connection
            ? "Сохранить настройки"
            : "Подключить и загрузить публикации"
      }}</Button>
      <p class="text-muted-foreground text-sm">
        {{
          connection?.isPaused
            ? "Проверка начнётся после продолжения работы."
            : "Проверка доступа запустится автоматически."
        }}
      </p>
    </div>
  </form>
</template>
