<script setup lang="ts">
import { computed } from "vue";
import { Archive, CloudUpload, LoaderCircle } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import type { ProductStatus } from "../../model/product.types";
import ProductFieldError from "../product/ProductFieldError.vue";

const props = defineProps<{
  id: string;
  status: ProductStatus;
  disabled: boolean;
  pending: boolean;
  error?: string;
}>();
const emit = defineEmits<{ change: [value: ProductStatus] }>();
const published = computed(() => props.status === "active");
const label = computed(() =>
  published.value
    ? "Опубликован"
    : props.status === "archived"
      ? "В архиве"
      : "Черновик",
);
</script>
<template>
  <FieldGroup class="gap-2">
    <Field
      orientation="horizontal"
      class="items-center justify-between"
      :data-invalid="!!error || undefined"
    >
      <FieldLabel as="span" class="sr-only">Статус товара</FieldLabel>
      <Badge
        :variant="published ? 'secondary' : 'outline'"
        role="status"
        aria-live="polite"
        >{{ label }}</Badge
      >
      <Button
        type="button"
        :variant="published ? 'outline' : 'default'"
        :disabled="disabled || pending"
        :aria-busy="pending"
        :aria-describedby="error ? `${id}-status-error` : undefined"
        @click="emit('change', published ? 'archived' : 'active')"
      >
        <LoaderCircle
          v-if="pending"
          class="animate-spin"
          data-icon="inline-start"
        />
        <Archive v-else-if="published" data-icon="inline-start" />
        <CloudUpload v-else data-icon="inline-start" />
        {{
          pending ? "Сохранение…" : published ? "Архивировать" : "Опубликовать"
        }}
      </Button>
    </Field>
    <ProductFieldError :id="`${id}-status-error`" :error="error" />
  </FieldGroup>
</template>
