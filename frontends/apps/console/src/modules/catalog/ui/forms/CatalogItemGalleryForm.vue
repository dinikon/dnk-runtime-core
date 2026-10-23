<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { ImagePlus, ArrowUp, ArrowDown, X, LoaderCircle } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { ProductGallery } from "../../model/product.types";
import {
  isProductImage,
  productImageAccept,
  productImageFormats,
} from "../../model/product-images";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  value: ProductGallery | null;
  pending: boolean;
  uploading?: boolean;
  reset: number;
  validationError?: string;
  imageUrl: (id: string) => string;
}>();
const emit = defineEmits<{
  save: [gallery: ProductGallery];
  upload: [file: File, main: boolean];
  dirty: [value: boolean];
}>();
const { value: gallery, change } = useProductSectionDraft(
  () => props.value ?? { images: [], primary_image_id: null },
  () => props.reset,
  (value) => {
    emit("dirty", true);
    emit("save", {
      ...value,
      images: value.images.map((i, position) => ({ ...i, position })),
    });
  },
);
const fileId = useId();
const fileInput = ref<HTMLInputElement | null>(null);
const localError = ref("");
const details = ref<Record<string, boolean>>({});
const error = computed(() => localError.value || props.validationError);
function move(index: number, delta: number): void {
  const images = [...gallery.value.images];
  const next = index + delta;
  if (next < 0 || next >= images.length) return;
  const [image] = images.splice(index, 1);
  if (image) images.splice(next, 0, image);
  change({ ...gallery.value, images });
}
function remove(id: string): void {
  const images = gallery.value.images.filter((i) => i.id !== id);
  change({
    images,
    primary_image_id:
      gallery.value.primary_image_id === id
        ? (images[0]?.id ?? null)
        : gallery.value.primary_image_id,
  });
}
function text(id: string, field: "alt" | "caption", value: string): void {
  change({
    ...gallery.value,
    images: gallery.value.images.map((i) =>
      i.id === id ? { ...i, [field]: value } : i,
    ),
  });
}
function upload(event: Event): void {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  localError.value = "";
  if (file) {
    if (!isProductImage(file))
      localError.value = `Выберите изображение: ${productImageFormats}.`;
    else if (file.size > 10 * 1024 * 1024)
      localError.value = "Размер изображения не должен превышать 10 МБ.";
    else if (gallery.value.images.length >= 100)
      localError.value = "В галерее может быть до 100 изображений.";
    else emit("upload", file, !gallery.value.images.length);
  }
  target.value = "";
}
</script>
<template>
  <fieldset :disabled="pending" class="min-w-0">
    <legend class="sr-only">Изображения и галерея</legend>
    <FieldGroup class="gap-4">
      <div
        v-if="gallery.images.length"
        class="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2"
      >
        <div
          v-for="(image, index) in gallery.images"
          :key="image.id"
          class="flex min-w-0 flex-col gap-3 rounded-lg border p-3"
        >
          <img
            :src="imageUrl(image.id)"
            :alt="image.alt"
            class="aspect-square w-full rounded-md bg-muted object-contain"
            loading="lazy"
          />
          <Badge
            v-if="gallery.primary_image_id === image.id"
            variant="secondary"
            class="self-start"
            >Главное изображение</Badge
          ><Button
            v-else
            type="button"
            variant="outline"
            :disabled="pending"
            @click="change({ ...gallery, primary_image_id: image.id })"
            >Сделать главным</Button
          >
          <Collapsible v-model:open="details[image.id]"
            ><CollapsibleTrigger as-child
              ><Button
                type="button"
                variant="ghost"
                class="min-h-11 w-full"
                :disabled="pending"
                >Описание и подпись</Button
              ></CollapsibleTrigger
            ><CollapsibleContent
              force-mount
              v-show="details[image.id]"
              class="pt-2"
              ><FieldGroup class="gap-3"
                ><Field
                  ><FieldLabel :for="`${image.id}-alt`"
                    >Описание изображения</FieldLabel
                  ><Input
                    :id="`${image.id}-alt`"
                    :model-value="image.alt"
                    @update:model-value="
                      text(image.id, 'alt', String($event))
                    " /></Field
                ><Field
                  ><FieldLabel :for="`${image.id}-caption`">Подпись</FieldLabel
                  ><Input
                    :id="`${image.id}-caption`"
                    :model-value="image.caption"
                    @update:model-value="
                      text(image.id, 'caption', String($event))
                    " /></Field></FieldGroup></CollapsibleContent
          ></Collapsible>
          <div class="flex flex-wrap gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              class="min-h-11 min-w-11"
              :disabled="pending || index === 0"
              :aria-label="`Переместить изображение ${index + 1} выше`"
              @click="move(index, -1)"
              ><ArrowUp /></Button
            ><Button
              type="button"
              variant="ghost"
              size="icon"
              class="min-h-11 min-w-11"
              :disabled="pending || index === gallery.images.length - 1"
              :aria-label="`Переместить изображение ${index + 1} ниже`"
              @click="move(index, 1)"
              ><ArrowDown /></Button
            ><Button
              type="button"
              variant="ghost"
              class="min-h-11 ml-auto"
              :disabled="pending"
              :aria-label="`Убрать изображение ${index + 1}`"
              @click="remove(image.id)"
              ><X data-icon="inline-start" />Убрать</Button
            >
          </div>
        </div>
      </div>
      <Field
        class="min-w-0 items-center gap-3 rounded-lg border border-dashed p-5 text-center"
        :data-invalid="!!error || undefined"
      >
        <ImagePlus class="size-7 text-muted-foreground" aria-hidden="true" />
        <FieldLabel :for="fileId" class="sr-only"
          >Загрузить изображение</FieldLabel
        ><input
          :id="fileId"
          ref="fileInput"
          type="file"
          :accept="productImageAccept"
          class="hidden"
          tabindex="-1"
          aria-hidden="true"
          :disabled="pending || gallery.images.length >= 100"
          :aria-describedby="`${fileId}-hint`"
          @change="upload"
        />
        <Button
          type="button"
          variant="outline"
          class="min-h-11 w-auto whitespace-normal"
          :disabled="pending || gallery.images.length >= 100"
          @click="fileInput?.click()"
          ><LoaderCircle
            v-if="uploading"
            class="animate-spin"
            data-icon="inline-start"
          />{{ uploading ? "Загрузка…" : "Загрузить изображение" }}</Button
        >
        <FieldDescription :id="`${fileId}-hint`"
          >{{ productImageFormats }} · до 10 МБ ·
          {{ gallery.images.length }}/100</FieldDescription
        > </Field
      ><ProductFieldError :id="`${fileId}-error`" :error="error" />
    </FieldGroup>
  </fieldset>
</template>
