<script setup lang="ts">
import { ref } from "vue";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import ProductFieldsBlock from "./ProductFieldsBlock.vue";
import CatalogItemGalleryForm from "../forms/CatalogItemGalleryForm.vue";
import type { CatalogItem, CatalogAttribute } from "../../model/catalog.types";
import type { ProductGallery, ProductSection } from "../../model/product.types";
defineProps<{
  item: CatalogItem;
  label: string;
  locale: string;
  pending: boolean;
  structureDirty: boolean;
  schemaVersion: number;
  attributes: CatalogAttribute[];
  dirtySections: ProductSection[];
  resets: Partial<Record<ProductSection, number>>;
  imageUrl: (imageId: string) => string;
}>();
defineEmits<{
  dirty: [section: ProductSection, value: boolean];
  save: [section: ProductSection, value: Record<string, unknown>];
  inherit: [section: "content" | "galleries"];
  upload: [file: File, main: boolean];
}>();
const current = ref("content");
const groups = [
  { id: "content", label: "Тексты", sections: ["content"] },
  { id: "general", label: "Основные", sections: ["price", "virtual"] },
  { id: "inventory", label: "Наличие", sections: ["status", "sku", "stock"] },
  { id: "shipping", label: "Доставка", sections: ["measurements"] },
  { id: "gallery", label: "Изображения", sections: [] },
  { id: "attributes", label: "Характеристики", sections: ["attributes"] },
  { id: "additional", label: "Дополнительно", sections: ["metadata"] },
] as const;
</script>
<template>
  <section
    class="flex min-w-0 flex-col gap-5 rounded-xl border bg-muted/10 p-3 md:p-5"
    :aria-label="`Редактор варианта: ${label}`"
  >
    <h3 class="break-words text-lg font-semibold">{{ label }}</h3>
    <p
      v-if="structureDirty"
      role="status"
      class="text-sm text-muted-foreground"
    >
      Сохраните или отмените изменения структуры, чтобы редактировать значения
      варианта.
    </p>
    <nav class="flex flex-wrap gap-1" aria-label="Разделы варианта">
      <Button
        v-for="group in groups"
        :key="group.id"
        :variant="current === group.id ? 'secondary' : 'ghost'"
        size="sm"
        :aria-pressed="current === group.id"
        :aria-label="group.label"
        @click="current = group.id"
        >{{ group.label
        }}<span
          v-if="
            group.sections.some((s) => dirtySections.includes(s)) ||
            (group.id === 'gallery' && dirtySections.includes('galleries'))
          "
          >•</span
        ></Button
      >
    </nav>
    <template v-for="group in groups" :key="group.id"
      ><div v-show="current === group.id" class="flex min-w-0 flex-col gap-5">
        <ProductFieldsBlock
          v-for="section in group.sections"
          :key="section"
          :item="item"
          :section="section"
          :locale="locale"
          :pending="pending || structureDirty"
          :reset="resets[section] ?? 0"
          :attributes="attributes"
          :schema-version="schemaVersion"
          :dirty="dirtySections.includes(section)"
          @dirty="$emit('dirty', section, $event)"
          @save="$emit('save', section, $event)"
          @inherit="$emit('inherit', 'content')"
        /></div
    ></template>
    <Card v-show="current === 'gallery'" class="shadow-none"
      ><CardHeader><CardTitle>Изображения варианта</CardTitle></CardHeader
      ><CardContent
        ><CatalogItemGalleryForm
          :own="item.own.galleries[locale] ?? null"
          :effective="item.effective.gallery"
          variant
          :pending="pending || structureDirty"
          :reset="resets.galleries ?? 0"
          :image-url="imageUrl"
          @dirty="$emit('dirty', 'galleries', $event)"
          @save="
            (gallery: ProductGallery) => $emit('save', 'galleries', { gallery })
          "
          @inherit="$emit('inherit', 'galleries')"
          @upload="(file, main) => $emit('upload', file, main)" /></CardContent
    ></Card>
  </section>
</template>
