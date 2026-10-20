<script setup lang="ts">
import { computed } from "vue";
import { ArrowLeft, ArrowRight, Star, Trash2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import type {
  ImportDraftValues,
  PublicationImportImage,
} from "../model/publication-import.types";
import {
  moveImportImage,
  removeImportImage,
} from "../model/publication-import-draft";
import { reasonLabel } from "../model/channels.presentation";
const props = defineProps<{
  values: ImportDraftValues;
  images: readonly PublicationImportImage[];
  disabled: boolean;
}>();
const emit = defineEmits<{ "update:values": [value: ImportDraftValues] }>();
const ordered = computed(() =>
  props.values.gallery
    .map((id) => props.images.find((image) => image.id === id))
    .filter((image): image is PublicationImportImage => !!image),
);
</script>
<template>
  <Card
    ><CardHeader
      ><CardTitle>Галерея</CardTitle
      ><CardDescription
        >Порядок и главное изображение будут перенесены в товар для всех
        языков.</CardDescription
      ></CardHeader
    >
    <CardContent>
      <Empty v-if="!ordered.length"
        ><EmptyHeader
          ><EmptyTitle>Фотографии не выбраны</EmptyTitle
          ><EmptyDescription
            >У источника нет галереи или вы исключили все
            фотографии.</EmptyDescription
          ></EmptyHeader
        ></Empty
      >
      <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="(image, index) in ordered"
          :key="image.id"
          class="flex min-w-0 flex-col gap-3 rounded-lg border p-3"
        >
          <img
            v-if="image.previewUrl"
            :src="image.previewUrl"
            loading="lazy"
            decoding="async"
            :alt="image.alt || `Фото ${index + 1}`"
            class="aspect-square w-full rounded-md object-contain bg-muted/30"
          />
          <div
            v-else
            class="flex aspect-square items-center justify-center rounded-md bg-muted p-4 text-center text-sm text-muted-foreground"
            role="status"
          >
            {{
              image.errorCode
                ? reasonLabel(image.errorCode)
                : "Переносим фотографию…"
            }}
          </div>
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm">Фото {{ index + 1 }}</span
            ><Badge
              v-if="values.primaryImageId === image.id"
              variant="secondary"
              >Главное</Badge
            >
          </div>
          <div class="flex flex-wrap gap-1">
            <Button
              type="button"
              size="icon"
              variant="outline"
              :aria-label="`Сделать фото ${index + 1} главным`"
              :disabled="
                disabled ||
                !image.previewUrl ||
                values.primaryImageId === image.id
              "
              @click="
                emit('update:values', { ...values, primaryImageId: image.id })
              "
              ><Star
            /></Button>
            <Button
              type="button"
              size="icon"
              variant="outline"
              :aria-label="`Переместить фото ${index + 1} раньше`"
              :disabled="disabled || index === 0"
              @click="
                emit('update:values', moveImportImage(values, image.id, -1))
              "
              ><ArrowLeft
            /></Button>
            <Button
              type="button"
              size="icon"
              variant="outline"
              :aria-label="`Переместить фото ${index + 1} позже`"
              :disabled="disabled || index === ordered.length - 1"
              @click="
                emit('update:values', moveImportImage(values, image.id, 1))
              "
              ><ArrowRight
            /></Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              :aria-label="`Исключить фото ${index + 1}`"
              :disabled="disabled"
              @click="
                emit('update:values', removeImportImage(values, image.id))
              "
              ><Trash2
            /></Button>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
