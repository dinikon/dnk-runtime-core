<script setup lang="ts">
import { FieldGroup } from "@/components/ui/field";
import type { CatalogItem } from "../../model/catalog.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import CatalogMeasurementField from "./CatalogMeasurementField.vue";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  item: CatalogItem;
  disabled: boolean;
  reset: number;
  error?: string;
}>();
const emit = defineEmits<{
  change: [value: Pick<CatalogItem, "weight" | "dimensions">];
}>();
const { value: measurements, change } = useProductSectionDraft(
  () => ({
    weight: props.item.weight,
    dimensions: props.item.dimensions ?? {
      length: null,
      width: null,
      height: null,
    },
  }),
  () => props.reset,
  (value) => emit("change", value),
);
</script>
<template>
  <fieldset
    :disabled="disabled"
    class="min-w-0"
    :aria-describedby="error ? 'measurements-error' : undefined"
  >
    <legend class="sr-only">Вес и размеры</legend>
    <FieldGroup class="gap-4"
      ><CatalogMeasurementField
        :model-value="measurements.weight"
        label="Вес"
        :units="['g', 'kg'] as const"
        default-unit="g"
        :effective="item.weight"
        @update:model-value="
          change({ ...measurements, weight: $event })
        " /><CatalogMeasurementField
        v-for="entry in [
          { key: 'length' as const, title: 'Длина' },
          { key: 'width' as const, title: 'Ширина' },
          { key: 'height' as const, title: 'Высота' },
        ]"
        :key="entry.key"
        :model-value="measurements.dimensions[entry.key]"
        :label="entry.title"
        :units="['cm', 'm'] as const"
        default-unit="cm"
        :effective="item.dimensions?.[entry.key] ?? null"
        @update:model-value="
          change({
            ...measurements,
            dimensions: { ...measurements.dimensions, [entry.key]: $event },
          })
        " /><ProductFieldError id="measurements-error" :error="error"
    /></FieldGroup>
  </fieldset>
</template>
