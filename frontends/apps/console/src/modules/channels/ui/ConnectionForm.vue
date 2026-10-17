<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import type { ConnectionSchema } from "../model/types";
const props = defineProps<{
  schema: ConnectionSchema;
  values: Record<string, string>;
  stored: string[];
  replacing: string[];
  errors: Record<string, string>;
  disabled: boolean;
}>();
const emit = defineEmits<{
  change: [key: string, value: string];
  replace: [key: string];
  cancelReplace: [key: string];
}>();
const field = (key: string) => props.schema.json_schema.properties[key]!;
</script>
<template>
  <FieldGroup>
    <Field
      v-for="item in schema.ui_schema"
      :key="item.property"
      :data-invalid="!!errors[item.property]"
      :data-disabled="disabled"
    >
      <FieldLabel :for="`connection-${item.property}`">{{
        field(item.property).title
      }}</FieldLabel>
      <div
        v-if="
          field(item.property).writeOnly &&
          stored.includes(item.property) &&
          !replacing.includes(item.property)
        "
        class="flex items-center gap-3"
      >
        <span class="text-sm text-muted-foreground">Ключ задан</span>
        <Button
          :id="`connection-${item.property}`"
          type="button"
          variant="outline"
          size="sm"
          :disabled="disabled"
          :aria-label="`Заменить ${field(item.property).title}`"
          @click="emit('replace', item.property)"
          >Заменить</Button
        >
      </div>
      <template v-else>
        <Input
          :id="`connection-${item.property}`"
          :model-value="values[item.property] ?? ''"
          :type="
            item.widget === 'password'
              ? 'password'
              : item.widget === 'url'
                ? 'url'
                : 'text'
          "
          :disabled="disabled"
          :required="schema.json_schema.required.includes(item.property)"
          :maxlength="field(item.property).maxLength"
          :autocomplete="
            field(item.property).writeOnly ? 'new-password' : 'off'
          "
          :aria-invalid="!!errors[item.property]"
          :aria-describedby="`hint-${item.property} error-${item.property}`"
          @update:model-value="emit('change', item.property, String($event))"
        />
        <Button
          v-if="stored.includes(item.property)"
          class="self-start"
          variant="ghost"
          size="sm"
          type="button"
          :disabled="disabled"
          @click="emit('cancelReplace', item.property)"
          >Оставить сохранённый ключ</Button
        >
      </template>
      <FieldDescription :id="`hint-${item.property}`">{{
        item.help_text ||
        (field(item.property).writeOnly
          ? "Сохранённый ключ не отображается."
          : "")
      }}</FieldDescription>
      <FieldError
        :id="`error-${item.property}`"
        :errors="[errors[item.property]]"
      />
    </Field>
  </FieldGroup>
</template>
