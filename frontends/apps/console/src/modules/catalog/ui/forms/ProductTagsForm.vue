<script setup lang="ts">
import { computed } from "vue";
import { FieldGroup } from "@/components/ui/field";
import type { CatalogTag } from "../../model/catalog.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import ProductReferencePicker from "./ProductReferencePicker.vue";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  ids: string[];
  tags: CatalogTag[];
  pending: boolean;
  disabled: boolean;
  reset: number;
  validationError?: string;
}>();
const emit = defineEmits<{
  submit: [ids: string[]];
  dirty: [value: boolean];
}>();
const { value: ids, change } = useProductSectionDraft(
  () => props.ids,
  () => props.reset,
  (value) => {
    emit("dirty", true);
    emit("submit", value);
  },
);
const options = computed(() =>
  props.tags.map((tag) => ({ id: tag.id, label: tag.label ?? "Нет перевода" })),
);
</script>
<template>
  <FieldGroup class="gap-3"
    ><ProductReferencePicker
      label="Метки"
      :ids="ids"
      :options="options"
      :disabled="disabled || pending"
      @change="change" /><ProductFieldError
      id="tags-error"
      :error="validationError"
  /></FieldGroup>
</template>
