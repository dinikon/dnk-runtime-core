<script setup lang="ts">
import { computed } from "vue";
import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldGroup,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type {
  JsonValue,
  SettingsSchema,
  ConnectionReferences,
} from "../model/channels.types";
import { arrayItemSchema } from "../model/settings-schema";
const props = defineProps<{
  schema: SettingsSchema;
  modelValue: JsonValue | undefined;
  path: string;
  required?: boolean;
  references: ConnectionReferences;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: JsonValue | undefined];
}>();
const objectValue = computed(() =>
  props.modelValue &&
  !Array.isArray(props.modelValue) &&
  typeof props.modelValue === "object"
    ? props.modelValue
    : {},
);
const arrayValue = computed(() =>
  Array.isArray(props.modelValue) ? props.modelValue : [],
);
const arraySlots = computed(() =>
  Math.min(
    props.schema.maxItems ?? 100,
    Math.max(props.schema.minItems ?? 0, arrayValue.value.length + 1),
  ),
);
const choices = computed(() => {
  const reference = props.schema["x-reference"];
  const codes =
    props.schema.enum ??
    (props.schema.const !== undefined ? [props.schema.const] : undefined);
  const options =
    reference === "locale"
      ? props.references.locales
      : reference === "currency"
        ? props.references.currencies
        : [];
  if (reference)
    return codes
      ? codes.map((code) => ({
          value: String(code),
          label: options.find((option) => option.code === code)?.name
            ? `${code} · ${options.find((option) => option.code === code)?.name}`
            : String(code),
        }))
      : options.map((option) => ({
          value: option.code,
          label: `${option.code} · ${option.name}`,
        }));
  return (
    codes?.map((value) => ({ value: String(value), label: String(value) })) ??
    []
  );
});
const scalar = computed(() =>
  props.modelValue === undefined || props.modelValue === null
    ? ""
    : String(props.modelValue),
);
function child(key: string, value: JsonValue | undefined): void {
  const next = { ...objectValue.value };
  if (value === undefined) delete next[key];
  else next[key] = value;
  emit("update:modelValue", next);
}
function item(index: number, value: JsonValue | undefined): void {
  const next = [...arrayValue.value];
  next[index] = value ?? "";
  while (
    next.length &&
    next.at(-1) === "" &&
    next.length > (props.schema.minItems ?? 0)
  )
    next.pop();
  emit("update:modelValue", next);
}
function scalarChanged(value: unknown): void {
  const raw = value === undefined || value === null ? "" : String(value);
  if (!raw && !props.required) {
    emit("update:modelValue", undefined);
    return;
  }
  if (props.schema.type === "number" || props.schema.type === "integer")
    emit("update:modelValue", raw ? Number(raw) : "");
  else if (props.schema.type === "boolean")
    emit("update:modelValue", raw === "true");
  else emit("update:modelValue", raw);
}
</script>
<template>
  <FieldGroup v-if="schema.type === 'object'">
    <FieldDescription v-if="schema.title">{{ schema.title }}</FieldDescription>
    <SchemaSettingsFields
      v-for="(field, key) in schema.properties"
      :key="key"
      :schema="field"
      :model-value="objectValue[key]"
      :path="`${path}-${key}`"
      :required="schema.required?.includes(String(key))"
      :references="references"
      @update:model-value="child(String(key), $event)"
    />
  </FieldGroup>
  <FieldGroup v-else-if="schema.type === 'array'">
    <SchemaSettingsFields
      v-for="position in arraySlots"
      :key="position"
      :schema="arrayItemSchema(schema, position - 1)"
      :model-value="arrayValue[position - 1]"
      :path="`${path}-${position}`"
      :required="position <= (schema.minItems ?? 0)"
      :references="references"
      @update:model-value="item(position - 1, $event)"
    />
    <FieldDescription v-if="schema.description">{{
      schema.description
    }}</FieldDescription>
  </FieldGroup>
  <Field v-else>
    <FieldLabel :for="path">{{ schema.title ?? path }}</FieldLabel>
    <Input
      v-if="schema.const !== undefined"
      :id="path"
      :model-value="
        choices.find((choice) => choice.value === scalar)?.label ?? scalar
      "
      readonly
    />
    <NativeSelect
      v-else-if="
        schema.enum || schema['x-reference'] || schema.type === 'boolean'
      "
      :id="path"
      :model-value="scalar"
      :required="required"
      @update:model-value="scalarChanged"
    >
      <NativeSelectOption value="" :disabled="required">{{
        required ? "Выберите значение" : "Не добавлять"
      }}</NativeSelectOption>
      <template v-if="schema.type === 'boolean'"
        ><NativeSelectOption value="true">Да</NativeSelectOption
        ><NativeSelectOption value="false">Нет</NativeSelectOption></template
      >
      <template v-else
        ><NativeSelectOption
          v-if="scalar && !choices.some((choice) => choice.value === scalar)"
          :value="scalar"
          >{{ scalar }} (недоступно)</NativeSelectOption
        ><NativeSelectOption
          v-for="choice in choices"
          :key="choice.value"
          :value="choice.value"
          >{{ choice.label }}</NativeSelectOption
        ></template
      >
    </NativeSelect>
    <Input
      v-else
      :id="path"
      :model-value="scalar"
      :type="
        schema.type === 'number' || schema.type === 'integer'
          ? 'number'
          : 'text'
      "
      :step="schema.type === 'integer' ? '1' : 'any'"
      :required="required"
      :minlength="schema.minLength"
      :maxlength="schema.maxLength"
      :pattern="schema.pattern"
      :min="schema.minimum"
      :max="schema.maximum"
      @update:model-value="scalarChanged"
    />
    <FieldDescription v-if="schema.description">{{
      schema.description
    }}</FieldDescription>
  </Field>
</template>
