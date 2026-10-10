<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { ProductVariant, CatalogAttribute } from "../model/catalog.types";
const props = defineProps<{
  variants: ProductVariant[];
  attributes: CatalogAttribute[];
  pending: boolean;
}>();
defineEmits<{ open: [id: string] }>();
function selection(variant: ProductVariant) {
  return Object.entries(variant.selection)
    .map(([id, optionId]) => {
      const attribute = props.attributes.find((a) => a.id === id),
        option = attribute?.options.find((o) => o.id === optionId);
      return `${attribute?.label ?? attribute?.code ?? id}: ${option?.label ?? option?.code ?? optionId}`;
    })
    .join(" · ");
}
</script>
<template>
  <div class="space-y-3">
    <div
      v-for="variant in variants"
      :key="variant.id"
      class="flex min-w-0 flex-wrap items-center justify-between gap-3 rounded-md border p-3"
    >
      <div class="min-w-0 flex-1 space-y-1">
        <p class="break-words font-medium">
          {{ variant.effectiveTitle ?? `Позиция ${variant.id}` }}
        </p>
        <p class="break-words text-sm text-muted-foreground">
          {{ selection(variant) }}
        </p>
        <p class="text-sm">
          {{ variant.virtual ? "Виртуальная" : "Физическая" }} ·
          {{
            variant.content === null ? "Перевод отсутствует" : "Перевод задан"
          }}
        </p>
      </div>
      <Button
        variant="outline"
        :disabled="pending"
        @click="$emit('open', variant.id)"
        >Открыть вариант</Button
      >
    </div>
  </div>
</template>
