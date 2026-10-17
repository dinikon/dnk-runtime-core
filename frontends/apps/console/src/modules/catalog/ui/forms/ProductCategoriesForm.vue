<script setup lang="ts">
import { computed } from "vue";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CatalogCategory } from "../../model/catalog.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import ProductReferencePicker from "./ProductReferencePicker.vue";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  ids: string[];
  primaryId: string | null;
  categories: CatalogCategory[];
  pending: boolean;
  disabled: boolean;
  reset: number;
  validationError?: string;
}>();
const emit = defineEmits<{
  submit: [ids: string[], primaryId: string | null];
  dirty: [value: boolean];
}>();
const { value: selection, change } = useProductSectionDraft(
  () => ({ ids: props.ids, primary: props.primaryId }),
  () => props.reset,
  (value) => {
    emit("dirty", true);
    emit("submit", value.ids, value.primary);
  },
);
function path(category: CatalogCategory): string {
  const names = [category.label ?? "Нет перевода"];
  const seen = new Set([category.id]);
  let parent = category.parentId;
  while (parent && !seen.has(parent)) {
    seen.add(parent);
    const entry = props.categories.find((c) => c.id === parent);
    if (!entry) break;
    names.unshift(entry.label ?? "Нет перевода");
    parent = entry.parentId;
  }
  return names.join(" / ");
}
const options = computed(() =>
  props.categories.map((c) => ({ id: c.id, label: path(c) })),
);
function select(ids: string[]): void {
  change({
    ids,
    primary:
      selection.value.primary && ids.includes(selection.value.primary)
        ? selection.value.primary
        : null,
  });
}
</script>
<template>
  <FieldGroup class="gap-4">
    <ProductReferencePicker
      label="Категории"
      :ids="selection.ids"
      :options="options"
      :disabled="disabled || pending"
      @change="select"
    />
    <Field
      v-if="selection.ids.length"
      :data-invalid="!!validationError || undefined"
      ><FieldLabel for="primary-category">Основная категория</FieldLabel
      ><Select
        :model-value="selection.primary ?? ''"
        :disabled="disabled || pending"
        @update:model-value="change({ ...selection, primary: String($event) })"
        ><SelectTrigger
          id="primary-category"
          class="w-full"
          :aria-invalid="!!validationError || undefined"
          :aria-describedby="validationError ? 'categories-error' : undefined"
          ><SelectValue placeholder="Выберите основную" /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem
              v-for="option in options.filter((o) =>
                selection.ids.includes(o.id),
              )"
              :key="option.id"
              :value="option.id"
              >{{ option.label }}</SelectItem
            ></SelectGroup
          ></SelectContent
        ></Select
      ></Field
    >
    <FieldDescription
      >Назначаются только выбранные категории. Родители не добавляются
      автоматически.</FieldDescription
    ><ProductFieldError id="categories-error" :error="validationError" />
  </FieldGroup>
</template>
