<script setup lang="ts">
import { computed, useId, ref, nextTick } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectGroup,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldSet,
  FieldLegend,
} from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { ChannelDraft, Platform, Channel } from "../model/channel.types";
import "./channel-workspace.css";
import ChannelSettingsSection from "./ChannelSettingsSection.vue";
import ChannelVerification from "./ChannelVerification.vue";
import { schemaFields } from "../model/channel.schema";
const props = defineProps<{
  draft: ChannelDraft;
  platform: Platform;
  platforms: Platform[];
  editing: boolean;
  busy: boolean;
  channel?: Channel;
  dirty?: boolean;
}>();
const emit = defineEmits<{
  change: [draft: ChannelDraft];
  platform: [kind: string];
  submit: [];
  verify: [];
}>();
const uid = useId();
const endpoints = computed(() => schemaFields(props.platform.configSchema));
const settings = computed(() =>
  schemaFields(props.platform.configSchema, "settings"),
);
const credentials = computed(() =>
  schemaFields(props.platform.credentialsSchema),
);
function value(
  section: "settings" | "credentials",
  key: string,
  next: string | number,
): void {
  emit("change", {
    ...props.draft,
    [section]: { ...props.draft[section], [key]: String(next) },
  });
}
function settingValue(key: string): string {
  const current = props.draft.settings[key];
  return typeof current === "string" ? current : "";
}
function settingLabel(value: unknown): string {
  const labels: Record<string, string> = {
    uk: "Українська",
    ru: "Русский",
    en: "English",
  };
  return Array.isArray(value)
    ? value.map((item) => labels[String(item)] ?? String(item)).join(" / ")
    : (labels[String(value)] ?? String(value ?? ""));
}
const reveals = ref<Record<string, number>>({});
async function submit(event: Event): Promise<void> {
  const form = event.target as HTMLFormElement;
  const invalid = [
    ...form.querySelectorAll<HTMLInputElement>("input:invalid, select:invalid"),
  ];
  if (invalid.length) {
    for (const input of invalid) {
      const group = input.closest<HTMLElement>("[data-channel-section]")
        ?.dataset.channelSection;
      if (group) reveals.value[group] = (reveals.value[group] ?? 0) + 1;
    }
    await nextTick();
    form.reportValidity();
    return;
  }
  emit("submit");
}
</script>
<template>
  <form class="channel-settings-form" novalidate @submit.prevent="submit">
    <div class="channel-settings-sections">
      <slot name="messages" />
      <ChannelSettingsSection
        title="Основные сведения"
        data-channel-section="general"
        :reveal="reveals.general"
      >
        <FieldGroup class="gap-3">
          <Field
            ><FieldLabel :for="uid + '-name'">Название подключения</FieldLabel
            ><Input
              :id="uid + '-name'"
              :model-value="draft.name"
              required
              :maxlength="255"
              :disabled="busy"
              @update:model-value="
                emit('change', { ...draft, name: String($event) })
              "
          /></Field>
          <Field
            ><FieldLabel
              :for="editing ? uid + '-platform' : undefined"
              :as="editing ? 'label' : 'span'"
              >Платформа</FieldLabel
            >
            <output v-if="editing" :id="uid + '-platform'" class="text-sm">{{
              platform.title
            }}</output>
            <ToggleGroup
              v-else
              type="single"
              variant="outline"
              :model-value="draft.platformKind"
              :disabled="busy"
              aria-label="Платформа"
              class="flex-wrap justify-start"
              @update:model-value="$event && emit('platform', String($event))"
              ><ToggleGroupItem
                v-for="p in platforms"
                :key="p.kind"
                :value="p.kind"
                >{{ p.title }}</ToggleGroupItem
              ></ToggleGroup
            >
          </Field>
          <Field v-for="field in endpoints" :key="field.key"
            ><FieldLabel :for="uid + '-' + field.key">{{
              field.key === "endpoint" ? "Адрес магазина" : field.title
            }}</FieldLabel
            ><Input
              :id="uid + '-' + field.key"
              :model-value="draft.endpoint"
              :readonly="field.readOnly"
              :required="field.required"
              type="url"
              :disabled="busy"
              :maxlength="field.maxLength"
              @update:model-value="
                emit('change', { ...draft, endpoint: String($event) })
              "
            /><FieldDescription v-if="!field.readOnly" class="text-xs"
              >HTTPS-адрес магазина, включая подпапку WordPress, если она
              есть.</FieldDescription
            ></Field
          >
        </FieldGroup>
      </ChannelSettingsSection>
      <ChannelSettingsSection
        v-if="settings.length"
        title="Настройки площадки"
        data-channel-section="settings"
        :reveal="reveals.settings"
      >
        <FieldGroup class="gap-3"
          ><Field v-for="field in settings" :key="field.key"
            ><FieldLabel :for="uid + '-setting-' + field.key">{{
              field.title
            }}</FieldLabel>
            <output
              v-if="field.readOnly"
              :id="uid + '-setting-' + field.key"
              class="text-sm"
              >{{ settingLabel(draft.settings[field.key]) }}</output
            >
            <Select
              v-else-if="field.options.length"
              :model-value="settingValue(field.key)"
              :disabled="busy"
              @update:model-value="
                $event && value('settings', field.key, String($event))
              "
              ><SelectTrigger :id="uid + '-setting-' + field.key"
                ><SelectValue /></SelectTrigger
              ><SelectContent
                ><SelectGroup
                  ><SelectItem
                    v-for="option in field.options"
                    :key="option"
                    :value="option"
                    >{{ settingLabel(option) }}</SelectItem
                  ></SelectGroup
                ></SelectContent
              ></Select
            >
            <Input
              v-else
              :id="uid + '-setting-' + field.key"
              :model-value="settingValue(field.key)"
              :required="field.required"
              :disabled="busy"
              :maxlength="field.maxLength"
              @update:model-value="value('settings', field.key, $event)"
            /> </Field
        ></FieldGroup>
      </ChannelSettingsSection>
      <ChannelSettingsSection
        title="Доступ к магазину"
        :default-open="!editing"
        data-channel-section="access"
        :reveal="reveals.access"
      >
        <FieldSet class="gap-3"
          ><FieldLegend class="sr-only">Данные доступа</FieldLegend
          ><FieldDescription v-if="editing" class="text-xs"
            >Сохранённые секреты не отображаются. Новый доступ заменит
            предыдущий и запустит проверку.</FieldDescription
          >
          <Field v-if="editing" orientation="horizontal"
            ><Checkbox
              :id="uid + '-replace'"
              :model-value="draft.replaceCredentials"
              :disabled="busy"
              @update:model-value="
                emit('change', {
                  ...draft,
                  replaceCredentials: $event === true,
                  credentials: Object.fromEntries(
                    credentials.map((f) => [f.key, '']),
                  ),
                })
              "
            /><FieldLabel :for="uid + '-replace'"
              >Заменить данные доступа</FieldLabel
            ></Field
          >
          <FieldGroup v-if="draft.replaceCredentials" class="gap-3"
            ><Field v-for="field in credentials" :key="field.key"
              ><FieldLabel :for="uid + '-secret-' + field.key">{{
                field.title
              }}</FieldLabel
              ><Input
                :id="uid + '-secret-' + field.key"
                :model-value="draft.credentials[field.key]"
                :type="field.secret ? 'password' : 'text'"
                :required="field.required"
                :disabled="busy"
                :maxlength="field.maxLength"
                autocomplete="new-password"
                @update:model-value="
                  value('credentials', field.key, $event)
                " /></Field
          ></FieldGroup>
        </FieldSet>
      </ChannelSettingsSection>
      <ChannelSettingsSection v-if="channel" title="Проверка подключения"
        ><ChannelVerification
          :channel="channel"
          :busy="busy"
          :dirty="!!dirty"
          @verify="emit('verify')"
      /></ChannelSettingsSection>
    </div>
    <div class="channel-settings-actions">
      <Button
        type="submit"
        class="w-full"
        :disabled="busy || (editing && !dirty)"
        >{{
          busy
            ? "Сохраняем…"
            : editing
              ? "Сохранить изменения"
              : "Создать и проверить"
        }}</Button
      >
    </div>
  </form>
</template>
