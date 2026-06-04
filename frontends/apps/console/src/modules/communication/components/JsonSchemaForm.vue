<script setup lang="ts">
import { computed, watch } from "vue";

import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type {
  CommunicationJsonSchema,
  JsonObject,
  JsonPrimitive,
  JsonValue,
} from "@/modules/communication/api";
import { defaultValueForSchema, schemaType } from "@/modules/communication/lib";

interface SchemaField {
  key: string;
  schema: CommunicationJsonSchema;
  required: boolean;
  label: string;
  description: string | null;
}

const props = withDefaults(
  defineProps<{
    schema: CommunicationJsonSchema | null | undefined;
    modelValue: JsonObject;
    uiSchema?: Record<string, JsonValue>;
    disabled?: boolean;
    secret?: boolean;
  }>(),
  {
    disabled: false,
    secret: false,
    uiSchema: () => ({}),
  },
);

const emit = defineEmits<{
  (event: "update:modelValue", value: JsonObject): void;
}>();

const fields = computed<SchemaField[]>(() => {
  const properties = props.schema?.properties ?? {};
  const requiredFields = new Set(props.schema?.required ?? []);

  return Object.entries(properties).map(([key, fieldSchema]) => ({
    key,
    schema: fieldSchema,
    required: requiredFields.has(key),
    label: fieldSchema.title ?? titleize(key),
    description: fieldSchema.description ?? null,
  }));
});

const hasFields = computed(() => fields.value.length > 0);

watch(
  () => [fields.value, props.modelValue] as const,
  ([currentFields]) => {
    const nextValue: JsonObject = { ...props.modelValue };
    let changed = false;

    for (const field of currentFields) {
      if (nextValue[field.key] === undefined) {
        nextValue[field.key] = defaultValueForSchema(field.schema);
        changed = true;
      }
    }

    if (changed) {
      emit("update:modelValue", nextValue);
    }
  },
  { immediate: true },
);

function titleize(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function fieldType(field: SchemaField) {
  return schemaType(field.schema);
}

function fieldWidget(field: SchemaField) {
  const config = props.uiSchema[field.key];

  if (config && typeof config === "object" && !Array.isArray(config)) {
    const widget = config["ui:widget"];

    if (typeof widget === "string") {
      return widget;
    }
  }

  if (fieldType(field) === "string" && (field.schema.maxLength ?? 0) > 255) {
    return "textarea";
  }

  return "input";
}

function inputType(field: SchemaField) {
  const type = fieldType(field);

  if (props.secret || field.schema.format === "password") {
    return "password";
  }

  if (field.schema.format === "email") {
    return "email";
  }

  if (type === "integer" || type === "number") {
    return "number";
  }

  return "text";
}

function fieldValue(field: SchemaField) {
  const value = props.modelValue[field.key];

  if (value === undefined || value === null) {
    return "";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return value;
}

function booleanValue(field: SchemaField) {
  return Boolean(props.modelValue[field.key]);
}

function enumValue(field: SchemaField) {
  return String(props.modelValue[field.key] ?? "");
}

function enumOptions(field: SchemaField) {
  return field.schema.enum ?? [];
}

function updateField(field: SchemaField, rawValue: string | number | boolean) {
  const nextValue = {
    ...props.modelValue,
    [field.key]: coerceFieldValue(field, rawValue),
  };

  emit("update:modelValue", nextValue);
}

function updateEnumField(field: SchemaField, event: Event) {
  const target = event.target;

  if (!(target instanceof HTMLSelectElement)) {
    return;
  }

  const option = enumOptions(field).find(
    (item) => String(item) === target.value,
  );

  updateField(field, option ?? target.value);
}

function coerceFieldValue(
  field: SchemaField,
  rawValue: string | number | boolean,
): JsonPrimitive {
  if (typeof rawValue === "boolean") {
    return rawValue;
  }

  const type = fieldType(field);
  const normalized = String(rawValue);

  if (!normalized && (type === "integer" || type === "number")) {
    return null;
  }

  if (type === "integer") {
    return Number.parseInt(normalized, 10);
  }

  if (type === "number") {
    return Number.parseFloat(normalized);
  }

  return normalized;
}
</script>

<template>
  <div v-if="hasFields" class="grid gap-4">
    <div v-for="field in fields" :key="field.key" class="grid gap-2">
      <div class="flex items-center justify-between gap-3">
        <label class="text-sm font-medium" :for="field.key">
          {{ field.label }}
        </label>
        <span v-if="field.required" class="text-xs text-muted-foreground">
          Required
        </span>
      </div>

      <template v-if="field.schema.enum?.length">
        <select
          :id="field.key"
          :value="enumValue(field)"
          :disabled="disabled"
          class="border-input bg-background h-9 w-full rounded-md border px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
          @change="updateEnumField(field, $event)"
        >
          <option
            v-for="option in enumOptions(field)"
            :key="String(option)"
            :value="String(option)"
          >
            {{ option }}
          </option>
        </select>
      </template>

      <Switch
        v-else-if="fieldType(field) === 'boolean'"
        :id="field.key"
        :model-value="booleanValue(field)"
        :disabled="disabled"
        @update:model-value="(value) => updateField(field, value)"
      />

      <Textarea
        v-else-if="fieldWidget(field) === 'textarea'"
        :id="field.key"
        class="min-h-28"
        :model-value="fieldValue(field)"
        :disabled="disabled"
        @update:model-value="(value) => updateField(field, value)"
      />

      <Input
        v-else
        :id="field.key"
        :type="inputType(field)"
        :model-value="fieldValue(field)"
        :disabled="disabled"
        @update:model-value="(value) => updateField(field, value)"
      />

      <p v-if="field.description" class="text-xs text-muted-foreground">
        {{ field.description }}
      </p>
    </div>
  </div>

  <p v-else class="text-sm text-muted-foreground">
    No schema fields are required.
  </p>
</template>
