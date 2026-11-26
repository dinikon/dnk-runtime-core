<script setup lang="ts">
import { computed } from "vue";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldGroup, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { cloneSchemaValue } from "../../model/feed-schema.clone";
import type {
  NodeFormControl,
  SchemaFieldDraft,
  SchemaIssue,
} from "../../model/feed-schema.types";

const props = defineProps<{
  modelValue: SchemaFieldDraft;
  controls: NodeFormControl[];
  issues: SchemaIssue[];
  disabled: boolean;
  xml: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: SchemaFieldDraft] }>();
const controls = computed(() =>
  props.controls.filter((control) => {
    if (control.path === "export.xml_placement")
      return props.xml && (
        props.modelValue.typeDefinition.kind !== "category" ||
        !!props.modelValue.export.publication
      );
    return /^(name|key|aiInstruction|export\.(name|enabled))$/.test(control.path);
  }),
);

function value(path: string): string | boolean {
  const field = props.modelValue;
  switch (path) {
    case "name": return field.label;
    case "key": return field.key;
    case "aiInstruction": return field.aiInstruction ?? "";
    case "export.name": return field.export.name;
    case "export.enabled": return field.export.enabled;
    case "export.xml_placement": return field.export.xmlPlacement;
    default: return "";
  }
}

function update(path: string, value: unknown): void {
  if (props.disabled) return;
  const field = cloneSchemaValue(props.modelValue);
  switch (path) {
    case "name": field.label = String(value); break;
    case "key": field.key = String(value); break;
    case "aiInstruction": field.aiInstruction = value ? String(value) : null; break;
    case "export.name": field.export.name = String(value); break;
    case "export.enabled": field.export.enabled = value === true; break;
    case "export.xml_placement":
      if (value !== "ATTRIBUTE" && value !== "ELEMENT") return;
      field.export.xmlPlacement = value;
      break;
    default: return;
  }
  emit("update:modelValue", field);
}

function issue(path: string): string | undefined {
  const keys = path === "name" ? ["name", "label"] : path.split(".");
  return props.issues.find((item) =>
    path === "name"
      ? keys.includes(String(item.path.at(-1))) && !item.path.includes("export")
      : keys.every((key) => item.path.includes(key)),
  )?.message;
}
</script>

<template>
  <FieldGroup>
    <Field
      v-for="(control, index) in controls"
      :key="control.path"
      :orientation="control.kind === 'checkbox' ? 'horizontal' : 'vertical'"
      :data-invalid="!!issue(control.path)"
    >
      <Checkbox
        v-if="control.kind === 'checkbox'"
        :id="`node-property-${index}`"
        :model-value="value(control.path) === true"
        :aria-invalid="!!issue(control.path)"
        :disabled="disabled"
        @update:model-value="update(control.path, $event)"
      />
      <FieldLabel :for="`node-property-${index}`">{{ control.label }}</FieldLabel>
      <Select
        v-if="control.kind === 'select'"
        :model-value="String(value(control.path))"
        :disabled="disabled"
        @update:model-value="update(control.path, $event)"
      >
        <SelectTrigger :id="`node-property-${index}`" :aria-invalid="!!issue(control.path)"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem v-for="option in control.options" :key="option" :value="option">
            {{ option === "ATTRIBUTE" ? "Атрибут" : option === "ELEMENT" ? "Элемент" : option }}
          </SelectItem>
        </SelectContent>
      </Select>
      <Textarea
        v-if="control.kind === 'textarea'"
        :id="`node-property-${index}`"
        :model-value="String(value(control.path))"
        :disabled="disabled"
        :maxlength="control.maxLength"
        :aria-invalid="!!issue(control.path)"
        @update:model-value="update(control.path, $event)"
      />
      <Input
        v-if="control.kind === 'input'"
        :id="`node-property-${index}`"
        :model-value="String(value(control.path))"
        :disabled="disabled"
        :maxlength="control.maxLength"
        :aria-invalid="!!issue(control.path)"
        @update:model-value="update(control.path, $event)"
      />
      <FieldError v-if="issue(control.path)">{{ issue(control.path) }}</FieldError>
    </Field>
  </FieldGroup>
</template>
