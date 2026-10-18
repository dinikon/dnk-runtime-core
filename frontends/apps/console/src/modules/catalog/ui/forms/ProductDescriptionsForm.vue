<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import ProductRichText from "../product/ProductRichText.vue";
import ProductFieldError from "../product/ProductFieldError.vue";
defineProps<{
  content: Record<string, string>;
  disabled: boolean;
  error?: string;
}>();
const emit = defineEmits<{
  change: [code: "body", value: string | undefined];
}>();
</script>
<template>
  <FieldGroup class="gap-3">
    <Field :data-invalid="!!error || undefined">
      <FieldLabel as="span">Описание товара</FieldLabel>
      <ProductRichText
        :model-value="content.body ?? ''"
        label="Описание товара"
        :disabled="disabled"
        :error-id="error ? 'body-error' : undefined"
        @update:model-value="emit('change', 'body', $event)"
      />
      <Button
        v-if="content.body !== undefined"
        type="button"
        variant="ghost"
        class="self-start"
        :disabled="disabled"
        @click="emit('change', 'body', undefined)"
        >Удалить описание</Button
      >
    </Field>
    <ProductFieldError id="body-error" :error="error" />
  </FieldGroup>
</template>
