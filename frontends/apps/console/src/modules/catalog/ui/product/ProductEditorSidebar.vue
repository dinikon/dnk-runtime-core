<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type {
  CatalogItem,
  CatalogCategory,
  CatalogTag,
} from "../../model/catalog.types";
import type { ProductSection } from "../../model/product.types";
import ProductFieldsBlock from "./ProductFieldsBlock.vue";
import CatalogItemGalleryForm from "../forms/CatalogItemGalleryForm.vue";
import ProductCategoriesForm from "../forms/ProductCategoriesForm.vue";
import ProductTagsForm from "../forms/ProductTagsForm.vue";
defineProps<{
  item: CatalogItem;
  locale: string;
  pending: boolean;
  blocked: boolean;
  uploading: boolean;
  errors: Partial<Record<ProductSection, string>>;
  schemaVersion: number;
  categories: CatalogCategory[];
  tags: CatalogTag[];
  dirtySections: ProductSection[];
  resets: Partial<Record<ProductSection, number>>;
  imageUrl: (imageId: string) => string;
}>();
const emit = defineEmits<{
  save: [section: ProductSection, value: Record<string, unknown>];
  dirty: [section: ProductSection, value: boolean];
  upload: [file: File, main: boolean];
  reload: [];
}>();
</script>
<template>
  <aside class="flex min-w-0 flex-col gap-6">
    <ProductFieldsBlock
      :key="`${item.id}:${locale}:status`"
      :validation-error="errors.status"
      :item="item"
      section="status"
      :locale="locale"
      :pending="blocked"
      :reset="resets.status ?? 0"
      :attributes="[]"
      :schema-version="schemaVersion"
      :dirty="dirtySections.includes('status')"
      @dirty="emit('dirty', 'status', $event)"
      @save="emit('save', 'status', $event)"
    />
    <Card class="shadow-none"
      ><CardHeader
        ><CardTitle
          >Изображения и галерея
          <span v-if="dirtySections.includes('galleries')" aria-hidden="true"
            >•</span
          ></CardTitle
        ></CardHeader
      ><CardContent
        ><CatalogItemGalleryForm
          :key="`${item.id}:${locale}:gallery`"
          :value="item.gallery"
          :pending="blocked || uploading"
          :validation-error="errors.galleries"
          :reset="resets.galleries ?? 0"
          :image-url="imageUrl"
          @dirty="emit('dirty', 'galleries', $event)"
          @save="(gallery) => emit('save', 'galleries', { gallery })"
          @upload="(file, main) => emit('upload', file, main)" /></CardContent
    ></Card>

    <Card class="shadow-none"
      ><CardHeader
        ><CardTitle
          >Категории
          <span v-if="dirtySections.includes('categories')">•</span></CardTitle
        ></CardHeader
      ><CardContent
        ><ProductCategoriesForm
          :key="`${item.id}:${locale}:categories`"
          :validation-error="errors.categories"
          :ids="item.category_ids"
          :primary-id="item.primary_category_id"
          :categories="categories"
          :pending="false"
          :disabled="blocked"
          :reset="resets.categories ?? 0"
          @dirty="emit('dirty', 'categories', $event)"
          @submit="
            (category_ids, primary_category_id) =>
              emit('save', 'categories', {
                category_ids,
                primary_category_id,
              })
          " /></CardContent
    ></Card>
    <Card class="shadow-none"
      ><CardHeader
        ><CardTitle
          >Метки <span v-if="dirtySections.includes('tags')">•</span></CardTitle
        ></CardHeader
      ><CardContent
        ><ProductTagsForm
          :key="`${item.id}:${locale}:tags`"
          :validation-error="errors.tags"
          :ids="item.tag_ids"
          :tags="tags"
          :pending="false"
          :disabled="blocked"
          :reset="resets.tags ?? 0"
          @dirty="emit('dirty', 'tags', $event)"
          @submit="
            (tag_ids) => emit('save', 'tags', { tag_ids })
          " /></CardContent
    ></Card>
    <Button variant="ghost" :disabled="pending" @click="emit('reload')"
      >Обновить данные товара</Button
    >
  </aside>
</template>
