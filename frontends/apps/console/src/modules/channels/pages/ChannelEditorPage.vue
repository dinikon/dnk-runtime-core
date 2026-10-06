<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { useUnsavedChanges } from "@/shared/model/use-unsaved-changes";
import { channelsApi, ChannelRequestError } from "../api/channels.api";
import {
  useChannelTenant,
  useChannel,
  useKinds,
  useChannelConfig,
} from "../model/queries";
import { supportedSchema, validateFields } from "../model/form";
import {
  statusLabels,
  typeLabels,
  type Channel,
  type UpdateChannel,
  type ChannelType,
} from "../model/types";
import ConnectionForm from "../ui/ConnectionForm.vue";

const props = withDefaults(defineProps<{ embedded?: boolean }>(), {
  embedded: false,
});
const route = useRoute(),
  router = useRouter(),
  client = useQueryClient();
const id = computed(() =>
  typeof route.params.channelId === "string" ? route.params.channelId : "",
);
const editing = computed(() => !!id.value);
const tenant = useChannelTenant();
const kinds = useKinds(),
  channel = useChannel(id);
const kind = ref(""),
  name = ref(""),
  active = ref(true),
  values = ref<Record<string, string>>({});
const replacing = ref<string[]>([]),
  original = ref<Channel | null>(null);
const config = useChannelConfig(kind);
const pending = ref(false),
  dirty = ref(false),
  error = ref(""),
  conflict = ref(false),
  deleteOpen = ref(false);
const fieldErrors = ref<Record<string, string>>({}),
  nameError = ref("");
const schema = computed(() => config.data.value?.config.connection);
const schemaSupported = computed(() => supportedSchema(schema.value));
const stored = computed(() => original.value?.configured_secret_fields ?? []);
const groups: ChannelType[] = ["marketplace", "cms", "shop"];
let operation: AbortController | null = null;
let generation = 0;
useUnsavedChanges(dirty, pending);
function hydrate(item: Channel) {
  original.value = item;
  kind.value = item.kind;
  name.value = item.name;
  active.value = item.is_active;
  values.value = { ...item.connection_settings };
  replacing.value = [];
  dirty.value = false;
}
function reset() {
  generation++;
  operation?.abort();
  operation = null;
  original.value = null;
  kind.value = "";
  name.value = "";
  active.value = true;
  values.value = {};
  replacing.value = [];
  dirty.value = false;
  pending.value = false;
  error.value = "";
  fieldErrors.value = {};
  nameError.value = "";
  conflict.value = false;
  deleteOpen.value = false;
}
watch([tenant, id], reset, { flush: "sync" });
watch(
  channel.data,
  (item) => {
    if (item && item.id === id.value && !dirty.value && !pending.value)
      hydrate(item);
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  generation++;
  operation?.abort();
  values.value = {};
});
function choose(next: string) {
  kind.value = next;
  values.value = {};
  replacing.value = [];
  fieldErrors.value = {};
  error.value = "";
  conflict.value = false;
  dirty.value = true;
}
function change(key: string, value: string) {
  values.value = { ...values.value, [key]: value };
  dirty.value = true;
  delete fieldErrors.value[key];
}
function replaceSecret(key: string) {
  replacing.value = [...replacing.value, key];
  change(key, "");
}
function cancelReplace(key: string) {
  replacing.value = replacing.value.filter((k) => k !== key);
  delete values.value[key];
  delete fieldErrors.value[key];
  dirty.value = true;
}
function clearSecrets() {
  const properties = schema.value?.json_schema.properties ?? {};
  values.value = Object.fromEntries(
    Object.entries(values.value).filter(([key]) => !properties[key]?.writeOnly),
  );
}
async function reloadConfig() {
  clearSecrets();
  replacing.value = [];
  fieldErrors.value = {};
  const result = await config.refetch();
  if (!result.isError) {
    conflict.value = false;
    error.value = "";
  }
}
async function save() {
  if (
    pending.value ||
    conflict.value ||
    !tenant.value ||
    !supportedSchema(schema.value) ||
    !config.data.value?.can_configure
  )
    return;
  nameError.value =
    name.value.trim().length < 1 || name.value.trim().length > 255
      ? "Название должно содержать 1–255 символов."
      : "";
  fieldErrors.value = validateFields(
    schema.value,
    values.value,
    stored.value,
    replacing.value,
  );
  if (nameError.value || Object.keys(fieldErrors.value).length) return;
  const settings = Object.fromEntries(
    Object.entries(values.value).filter(([key, value]) => {
      const prop = schema.value!.json_schema.properties[key];
      return (
        prop &&
        (!editing.value ||
          (prop.writeOnly
            ? replacing.value.includes(key)
            : value !== original.value?.connection_settings[key]))
      );
    }),
  );
  const payload: UpdateChannel = {
    name: name.value.trim(),
    is_active: active.value,
  };
  if (Object.keys(settings).length || !editing.value) {
    payload.connection_settings = settings;
    payload.config_version = config.data.value.config_version;
  }
  const requestGeneration = generation,
    requestTenant = tenant.value;
  pending.value = true;
  error.value = "";
  operation = new AbortController();
  try {
    const result = editing.value
      ? await channelsApi.update(id.value, payload, operation.signal)
      : await channelsApi.create(
          {
            name: payload.name!,
            kind: kind.value,
            is_active: active.value,
            config_version: config.data.value.config_version,
            connection_settings: settings,
          },
          operation.signal,
        );
    if (requestGeneration !== generation) return;
    clearSecrets();
    hydrate(result);
    client.setQueryData(
      ["channels", requestTenant, "detail", result.id],
      result,
    );
    await client.invalidateQueries({
      queryKey: ["channels", requestTenant, "list"],
    });
    if (requestGeneration !== generation) return;
    pending.value = false;
    await client.invalidateQueries({
      queryKey: ["channels", requestTenant, "publications", result.id],
    });
    await client.invalidateQueries({
      queryKey: ["channels", requestTenant, "imports", result.id],
    });
    toast.success("Канал сохранён");
    if (!editing.value) await router.push(`/channels/${result.id}`);
  } catch (reason) {
    if (requestGeneration !== generation) return;
    error.value =
      reason instanceof Error ? reason.message : "Не удалось сохранить канал.";
    if (reason instanceof ChannelRequestError) {
      conflict.value = reason.status === 409;
      nameError.value = reason.fields.name ?? "";
      for (const [key, message] of Object.entries(reason.fields))
        if (key.startsWith("connection_settings."))
          fieldErrors.value[key.slice("connection_settings.".length)] = message;
    }
  } finally {
    // The request object is never put into a mutation/query cache.
    for (const key of Object.keys(settings)) delete settings[key];
    if (requestGeneration === generation) {
      pending.value = false;
      operation = null;
    }
  }
}
async function remove() {
  if (pending.value || !id.value) return;
  const requestGeneration = generation,
    requestTenant = tenant.value,
    requestId = id.value;
  pending.value = true;
  error.value = "";
  operation = new AbortController();
  try {
    await channelsApi.remove(requestId, operation.signal);
    if (requestGeneration !== generation) return;
    dirty.value = false;
    clearSecrets();
    deleteOpen.value = false;
    client.removeQueries({
      queryKey: ["channels", requestTenant, "detail", requestId],
    });
    await client.invalidateQueries({
      queryKey: ["channels", requestTenant, "list"],
    });
    if (requestGeneration !== generation) return;
    pending.value = false;
    client.removeQueries({
      queryKey: ["channels", requestTenant, "publications", requestId],
    });
    client.removeQueries({
      queryKey: ["channels", requestTenant, "imports", requestId],
    });
    toast.success("Канал удалён");
    await router.push("/channels");
  } catch (reason) {
    if (requestGeneration === generation)
      error.value =
        reason instanceof Error ? reason.message : "Не удалось удалить канал.";
  } finally {
    if (requestGeneration === generation) {
      pending.value = false;
      operation = null;
    }
  }
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header
      v-if="!props.embedded"
      class="flex flex-wrap items-center justify-between gap-3"
    >
      <h1 class="text-2xl font-semibold">
        {{ editing ? "Настройки канала" : "Добавить канал" }}
      </h1>
      <Button as-child variant="outline"
        ><RouterLink to="/channels">К каналам</RouterLink></Button
      >
    </header>
    <Skeleton
      v-if="kinds.isPending.value || (editing && channel.isPending.value)"
      class="h-64"
      aria-label="Загрузка настроек"
    />
    <Alert
      v-else-if="kinds.isError.value || (editing && channel.isError.value)"
      variant="destructive"
      ><AlertTitle>Не удалось загрузить данные</AlertTitle
      ><AlertDescription
        ><Button
          variant="outline"
          @click="
            kinds.refetch();
            channel.refetch();
          "
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <template v-else>
      <Card v-if="!editing && !kind">
        <CardHeader
          ><CardTitle>1. Выберите платформу</CardTitle
          ><CardDescription
            >Доступные подключения определяет ваша платформа.</CardDescription
          ></CardHeader
        >
        <CardContent class="flex flex-col gap-6"
          ><section
            v-for="group in groups"
            :key="group"
            class="flex flex-col gap-3"
          >
            <h2 class="font-medium">{{ typeLabels[group] }}</h2>
            <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <div
                v-for="item in (kinds.data.value ?? []).filter(
                  (k) => k.type === group,
                )"
                :key="item.kind"
                class="flex flex-col gap-1"
              >
                <Button
                  variant="outline"
                  class="justify-start"
                  :disabled="!item.can_configure"
                  @click="choose(item.kind)"
                  >{{ item.label }}</Button
                >
                <p
                  v-if="!item.can_configure"
                  class="text-xs text-muted-foreground"
                >
                  {{ item.unavailable_reason }}
                </p>
              </div>
            </div>
          </section></CardContent
        >
      </Card>
      <Card v-else class="max-w-3xl">
        <CardHeader
          ><CardTitle>{{
            editing ? original?.name : "2. Настройте подключение"
          }}</CardTitle
          ><CardDescription
            >{{ kinds.data.value?.find((k) => k.kind === kind)?.label }} ·
            {{
              config.data.value ? typeLabels[config.data.value.type] : ""
            }}</CardDescription
          >
          <div v-if="original" class="flex flex-wrap gap-2">
            <Badge variant="secondary">{{
              statusLabels[original.status]
            }}</Badge
            ><Badge variant="outline">{{
              original.is_active ? "Включён" : "Выключен"
            }}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <Skeleton
            v-if="config.isPending.value"
            class="h-48"
            aria-label="Загрузка формы подключения"
          />
          <Alert v-else-if="config.isError.value" variant="destructive"
            ><AlertTitle>Не удалось загрузить форму</AlertTitle
            ><AlertDescription
              ><Button variant="outline" @click="config.refetch()"
                >Повторить</Button
              ></AlertDescription
            ></Alert
          >
          <Alert
            v-else-if="!schemaSupported || !config.data.value?.can_configure"
            variant="destructive"
            ><AlertTitle
              >Эта форма подключения пока не поддерживается</AlertTitle
            ><AlertDescription
              >Обновите Console или выберите другую платформу.</AlertDescription
            ></Alert
          >
          <form
            v-else
            id="channel-form"
            class="flex flex-col gap-6"
            novalidate
            @submit.prevent="save"
          >
            <FieldGroup>
              <Field :data-invalid="!!nameError"
                ><FieldLabel for="channel-name">Название канала</FieldLabel
                ><Input
                  id="channel-name"
                  :model-value="name"
                  :disabled="pending"
                  maxlength="255"
                  required
                  :aria-invalid="!!nameError"
                  aria-describedby="channel-name-error"
                  @update:model-value="
                    name = String($event);
                    dirty = true;
                    nameError = '';
                  " /><FieldError id="channel-name-error" :errors="[nameError]"
              /></Field>
              <Field orientation="horizontal"
                ><Switch
                  id="channel-active"
                  :model-value="active"
                  :disabled="pending"
                  @update:model-value="
                    active = $event;
                    dirty = true;
                  "
                />
                <div>
                  <FieldLabel for="channel-active">Канал включён</FieldLabel
                  ><FieldDescription
                    >Активность не подтверждает доступ к
                    магазину.</FieldDescription
                  >
                </div></Field
              >
            </FieldGroup>
            <ConnectionForm
              v-if="schema"
              :schema="schema"
              :values="values"
              :stored="stored"
              :replacing="replacing"
              :errors="fieldErrors"
              :disabled="pending || conflict"
              @change="change"
              @replace="replaceSecret"
              @cancel-replace="cancelReplace"
            />
            <Alert v-if="['prom', 'woocommerce'].includes(kind)">
              <AlertTitle>Публикации из магазина</AlertTitle>
              <AlertDescription v-if="editing">
                Загрузите или обновите карточки на вкладке «Публикации».
              </AlertDescription>
              <AlertDescription v-else-if="active">
                После сохранения канала начнётся загрузка публикаций.
              </AlertDescription>
              <AlertDescription v-else>
                Включите канал, чтобы загрузить публикации.
              </AlertDescription>
            </Alert>
            <Alert v-if="error" variant="destructive"
              ><AlertTitle>Не удалось выполнить действие</AlertTitle
              ><AlertDescription
                >{{ error
                }}<Button
                  v-if="conflict"
                  type="button"
                  variant="outline"
                  :disabled="config.isFetching.value"
                  @click="reloadConfig"
                  >Обновить форму</Button
                ></AlertDescription
              ></Alert
            >
          </form>
        </CardContent>
        <CardFooter class="flex flex-wrap justify-between gap-3">
          <div class="flex flex-wrap gap-2">
            <Button
              type="submit"
              form="channel-form"
              :disabled="
                pending ||
                conflict ||
                !schemaSupported ||
                config.isError.value ||
                !config.data.value?.can_configure
              "
              >{{ pending ? "Сохранение…" : "Сохранить канал" }}</Button
            ><Button
              v-if="!editing"
              variant="outline"
              :disabled="pending"
              @click="choose('')"
              >Выбрать другую платформу</Button
            >
          </div>
          <Button
            v-if="editing"
            variant="destructive"
            :disabled="pending"
            @click="deleteOpen = true"
            >Удалить канал</Button
          >
        </CardFooter>
      </Card>
    </template>
    <AlertDialog
      :open="deleteOpen"
      @update:open="!pending && (deleteOpen = $event)"
      ><AlertDialogContent
        ><AlertDialogHeader
          ><AlertDialogTitle
            >Удалить канал «{{ original?.name }}»?</AlertDialogTitle
          ><AlertDialogDescription
            >Настройки, ключи подключения и локальные публикации этого канала
            будут удалены. Данные внешнего магазина не
            изменятся.</AlertDialogDescription
          ></AlertDialogHeader
        >
        <p v-if="error" role="alert" class="text-sm text-destructive">
          {{ error }}
        </p>
        <AlertDialogFooter
          ><AlertDialogCancel :disabled="pending">Отмена</AlertDialogCancel
          ><Button variant="destructive" :disabled="pending" @click="remove">{{
            pending ? "Удаление…" : "Удалить"
          }}</Button></AlertDialogFooter
        ></AlertDialogContent
      ></AlertDialog
    >
  </div>
</template>
