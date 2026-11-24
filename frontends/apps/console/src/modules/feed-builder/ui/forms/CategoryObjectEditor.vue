<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { CategoryProperty, CategoryPropertyDefinition } from "../../model/feed-categories.types";

const props = defineProps<{
  fields: CategoryPropertyDefinition[];
  values: Record<string, CategoryProperty>;
  idKey: string;
  saved: boolean;
  catalogLinked: boolean;
  disabled: boolean;
}>();
const emit = defineEmits<{ change: [values: Record<string, CategoryProperty>] }>();

function update(property: CategoryPropertyDefinition, input: string): void {
  const values = { ...props.values };
  if (input === "") delete values[property.key];
  else if (property.kind === "integer") {
    if (!/^-?\d+$/.test(input) || !Number.isSafeInteger(Number(input))) return;
    values[property.key] = Number(input);
  } else {
    values[property.key] = property.kind === "boolean" ? input === "true" : input;
  }
  emit("change", values);
}
</script>

<template>
  <fieldset class="grid gap-3" :disabled="disabled">
    <label v-for="property in fields" :key="property.key" class="grid gap-1 text-sm">
      <span>{{ property.key }}<span v-if="property.required && property.key !== idKey" aria-hidden="true"> *</span></span>
      <Textarea
        v-if="property.kind === 'text'"
        :aria-label="property.key"
        :model-value="String(values[property.key] ?? '')"
        :placeholder="catalogLinked && property.source ? 'Название из Catalog' : undefined"
        :readonly="property.key === idKey && saved"
        @update:model-value="update(property, String($event))"
      />
      <select
        v-else-if="property.kind === 'boolean'"
        class="w-full rounded-md border bg-background px-2 py-2"
        :aria-label="property.key"
        :value="String(values[property.key] ?? '')"
        @change="update(property, ($event.target as HTMLSelectElement).value)"
      >
        <option value="">Не задано</option>
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
      <Input
        v-else
        :aria-label="property.key"
        :model-value="String(values[property.key] ?? '')"
        :inputmode="property.kind === 'integer' ? 'numeric' : 'text'"
        :placeholder="property.key === idKey ? 'ID назначится при сохранении' : catalogLinked && property.source ? 'Название из Catalog' : undefined"
        :readonly="property.key === idKey && saved"
        @update:model-value="update(property, String($event))"
      />
    </label>
  </fieldset>
</template>
