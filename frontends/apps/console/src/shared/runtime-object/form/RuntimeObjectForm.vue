<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  RuntimeFieldDescription,
  RuntimeObjectMutationPayload,
  RuntimeObjectRecord,
} from "@/shared/runtime-object";
import RuntimeMultiSelect from "./RuntimeMultiSelect.vue";

type RuntimeFormValue = string | string[] | null;

const props = withDefaults(
  defineProps<{
    fields: RuntimeFieldDescription[];
    record?: RuntimeObjectRecord | null;
    mode: "create" | "edit";
    isSubmitting?: boolean;
    error?: string | null;
  }>(),
  {
    record: null,
    isSubmitting: false,
    error: null,
  },
);

const emit = defineEmits<{
  (event: "submit", payload: RuntimeObjectMutationPayload): void;
  (event: "cancel"): void;
}>();

const values = reactive<Record<string, RuntimeFormValue>>({});
const errors = ref<Record<string, string>>({});

const editableFields = computed(() =>
  props.fields.filter((field) => field.kind !== "system"),
);

watch(
  [() => props.fields, () => props.record, () => props.mode],
  () => {
    resetForm();
  },
  { immediate: true },
);

function resetForm() {
  errors.value = {};

  for (const key of Object.keys(values)) {
    delete values[key];
  }

  for (const field of editableFields.value) {
    values[field.field_name] = initialValue(field);
  }
}

function initialValue(field: RuntimeFieldDescription): RuntimeFormValue {
  const existingValue = props.record?.[field.field_name];

  if (existingValue !== undefined) {
    if (field.type === "multiselect") {
      return Array.isArray(existingValue)
        ? existingValue.map((item) => String(item))
        : [];
    }

    return existingValue === null ? "" : String(existingValue);
  }

  if (field.type === "multiselect") {
    return [];
  }

  const normalizedDefault = normalizeDefaultValue(field.default_value);
  if (normalizedDefault !== null) {
    return normalizedDefault;
  }

  return "";
}

function normalizeDefaultValue(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  if (value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1);
  }

  return value;
}

function getStringValue(fieldName: string): string {
  const value = values[fieldName];
  return typeof value === "string" ? value : "";
}

function setStringValue(fieldName: string, value: unknown) {
  values[fieldName] =
    value === null || value === undefined ? "" : String(value);
}

function getArrayValue(fieldName: string): string[] {
  const value = values[fieldName];
  return Array.isArray(value) ? value : [];
}

function setArrayValue(fieldName: string, value: string[]) {
  values[fieldName] = value;
}

function submitForm() {
  const nextErrors: Record<string, string> = {};
  const payload: RuntimeObjectMutationPayload = {};

  for (const field of editableFields.value) {
    const rawValue = values[field.field_name];

    if (field.type === "multiselect") {
      const listValue = Array.isArray(rawValue) ? rawValue : [];
      if (!field.is_nullable && listValue.length === 0) {
        nextErrors[field.field_name] = `${field.label} is required.`;
      }
      payload[field.field_name] = listValue;
      continue;
    }

    const stringValue = typeof rawValue === "string" ? rawValue.trim() : "";
    if (!field.is_nullable && !stringValue) {
      nextErrors[field.field_name] = `${field.label} is required.`;
    }
    payload[field.field_name] =
      stringValue === "" && field.is_nullable ? null : stringValue;
  }

  errors.value = nextErrors;
  if (Object.keys(nextErrors).length > 0) {
    return;
  }

  emit("submit", payload);
}
</script>

<template>
  <form class="flex min-h-0 flex-1 flex-col" @submit.prevent="submitForm">
    <div class="min-h-0 flex-1 overflow-y-auto px-1">
      <Alert v-if="error" variant="destructive" class="mb-4">
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <FieldGroup>
        <Field v-for="field in editableFields" :key="field.field_name">
          <FieldLabel :for="field.field_name">
            {{ field.label }}
            <span v-if="!field.is_nullable" class="text-destructive">*</span>
          </FieldLabel>

          <RuntimeMultiSelect
            v-if="field.type === 'multiselect'"
            :model-value="getArrayValue(field.field_name)"
            :options="field.options"
            :placeholder="`Select ${field.label.toLowerCase()}`"
            @update:model-value="setArrayValue(field.field_name, $event)"
          />

          <Select
            v-else-if="field.type === 'select'"
            :model-value="getStringValue(field.field_name)"
            @update:model-value="setStringValue(field.field_name, $event)"
          >
            <SelectTrigger :id="field.field_name" class="w-full">
              <SelectValue
                :placeholder="`Select ${field.label.toLowerCase()}`"
              />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-if="field.is_nullable" value=""> None </SelectItem>
              <SelectItem
                v-for="option in field.options"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </SelectItem>
            </SelectContent>
          </Select>

          <Input
            v-else
            :id="field.field_name"
            :type="field.type === 'datetime' ? 'datetime-local' : 'text'"
            :model-value="getStringValue(field.field_name)"
            @update:model-value="setStringValue(field.field_name, $event)"
          />

          <FieldDescription v-if="field.description">
            {{ field.description }}
          </FieldDescription>
          <FieldError v-if="errors[field.field_name]">
            {{ errors[field.field_name] }}
          </FieldError>
        </Field>
      </FieldGroup>
    </div>

    <div class="mt-6 flex justify-end gap-2 border-t pt-4">
      <Button
        type="button"
        variant="outline"
        :disabled="isSubmitting"
        @click="emit('cancel')"
      >
        Cancel
      </Button>
      <Button type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "Saving..." : "Save" }}
      </Button>
    </div>
  </form>
</template>
