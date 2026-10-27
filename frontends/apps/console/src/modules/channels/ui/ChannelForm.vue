<script setup lang="ts">
import { computed, useId } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldSet,
  FieldLegend,
} from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { ChannelDraft, Platform } from "../model/channel.types";
import { schemaFields } from "../model/channel.schema";
const props = defineProps<{
  draft: ChannelDraft;
  platform: Platform;
  platforms: Platform[];
  editing: boolean;
  busy: boolean;
}>();
const emit = defineEmits<{
  change: [draft: ChannelDraft];
  platform: [kind: string];
  submit: [];
}>();
const uid = useId();
const endpoints = computed(() =>
  schemaFields(props.platform.configSchema).filter((field) => !field.readOnly),
);
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
</script>
<template>
  <form class="flex flex-col gap-6" @submit.prevent="emit('submit')">
    <FieldGroup
      ><Field
        ><FieldLabel :for="uid + '-name'">Название канала</FieldLabel
        ><Input
          :id="uid + '-name'"
          :model-value="draft.name"
          required
          :maxlength="255"
          :disabled="busy"
          @update:model-value="
            emit('change', { ...draft, name: String($event) })
          " /></Field
      ><Field v-if="!editing"
        ><FieldLabel>Платформа</FieldLabel
        ><ToggleGroup
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
        ></Field
      ><Field v-for="field in endpoints" :key="field.key"
        ><FieldLabel :for="uid + '-' + field.key">{{ field.title }}</FieldLabel
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
        /><FieldDescription v-if="!field.readOnly"
          >HTTPS-адрес магазина. Если WordPress установлен в подпапке, укажите
          её в адресе.</FieldDescription
        ></Field
      ><Field v-for="field in settings" :key="field.key"
        ><FieldLabel :for="uid + '-setting-' + field.key">{{
          field.title
        }}</FieldLabel
        ><Input
          :id="uid + '-setting-' + field.key"
          :model-value="draft.settings[field.key]"
          :required="field.required"
          :disabled="busy"
          :maxlength="field.maxLength"
          @update:model-value="
            value('settings', field.key, $event)
          " /></Field></FieldGroup
    ><FieldSet
      ><FieldLegend>Доступ к магазину</FieldLegend
      ><FieldDescription v-if="editing"
        >Сохранённые секреты не отображаются. Новый доступ сразу заменит
        предыдущий и запустит проверку.</FieldDescription
      ><Field v-if="editing" orientation="horizontal"
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
      ><FieldGroup v-if="draft.replaceCredentials"
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
            " /></Field></FieldGroup></FieldSet
    ><Button type="submit" class="self-start" :disabled="busy">{{
      busy
        ? "Сохраняем…"
        : editing
          ? "Сохранить изменения"
          : "Создать и проверить"
    }}</Button>
  </form>
</template>
