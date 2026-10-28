<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { CatalogItem } from "../../model/catalog.types";
defineProps<{
  item: CatalogItem;
  overrides: Record<string, string>;
  disabled: boolean;
  imageUrl: (id: string) => string;
}>();
const emit = defineEmits<{
  inheritContent: [code: "title" | "body"];
  ownContent: [code: "title" | "body"];
  clearBody: [];
  gallery: [mode: "inherit" | "empty"];
  measurements: [name: "weight" | "dimensions"];
}>();
</script>
<template>
  <Card class="gap-3 py-4"
    ><CardHeader class="px-4"
      ><CardTitle>Наследование от карточки</CardTitle></CardHeader
    ><CardContent class="flex flex-col gap-4 px-4">
      <div
        v-for="code in ['title', 'body'] as const"
        :key="code"
        class="flex flex-wrap items-center gap-2 text-sm"
      >
        <span class="min-w-24 font-medium">{{
          code === "title" ? "Название" : "Описание"
        }}</span>
        <span class="text-muted-foreground">{{
          code in overrides ? "Своё значение" : "Родительское значение"
        }}</span>
        <Button
          v-if="code in overrides"
          size="sm"
          variant="outline"
          :disabled="disabled"
          @click="emit('inheritContent', code)"
          >Использовать родительское</Button
        >
        <Button
          v-else
          size="sm"
          variant="outline"
          :disabled="disabled || item.effective_content?.[code] === undefined"
          @click="emit('ownContent', code)"
          >Задать своё</Button
        >
        <Button
          v-if="code === 'body'"
          size="sm"
          variant="ghost"
          :disabled="disabled"
          @click="emit('clearBody')"
          >Очистить описание</Button
        >
      </div>
      <div class="flex flex-wrap items-center gap-2 text-sm">
        <span class="min-w-24 font-medium">Галерея</span
        ><span class="text-muted-foreground">{{
          item.gallery === null ? "Родительская" : "Своя"
        }}</span>
        <Button
          v-if="item.gallery !== null"
          size="sm"
          variant="outline"
          :disabled="disabled"
          @click="emit('gallery', 'inherit')"
          >Использовать родительскую</Button
        >
        <Button
          size="sm"
          variant="outline"
          :disabled="disabled"
          @click="emit('gallery', 'empty')"
          >{{
            item.gallery === null ? "Задать свою галерею" : "Очистить галерею"
          }}</Button
        >
      </div>
      <div
        v-if="item.gallery === null && item.effective_gallery?.images.length"
        class="flex flex-wrap gap-2"
        aria-label="Изображения родителя"
      >
        <img
          v-for="image in item.effective_gallery.images.slice(0, 6)"
          :key="image.id"
          :src="imageUrl(image.id)"
          :alt="image.alt"
          class="size-12 rounded-md border object-contain"
        />
      </div>
      <div
        v-for="name in ['weight', 'dimensions'] as const"
        :key="name"
        class="flex flex-wrap items-center gap-2 text-sm"
      >
        <span class="min-w-24 font-medium">{{
          name === "weight" ? "Вес" : "Габариты"
        }}</span
        ><span class="text-muted-foreground">{{
          item[name] === null ? "Родительские значения" : "Свои значения"
        }}</span
        ><Button
          v-if="item[name] !== null"
          size="sm"
          variant="outline"
          :disabled="disabled"
          @click="emit('measurements', name)"
          >Использовать родительские</Button
        ><span
          v-else-if="name === 'weight' && item.effective_weight"
          class="text-muted-foreground"
          >{{ item.effective_weight.value }}
          {{ item.effective_weight.unit }}</span
        ><span
          v-else-if="name === 'dimensions' && item.effective_dimensions"
          class="text-muted-foreground"
          >{{
            [
              item.effective_dimensions.length,
              item.effective_dimensions.width,
              item.effective_dimensions.height,
            ]
              .map((v) => (v ? v.value + " " + v.unit : "—"))
              .join(" × ")
          }}</span
        >
      </div>
    </CardContent></Card
  >
</template>
