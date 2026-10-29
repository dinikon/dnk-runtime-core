<script setup lang="ts">
import { computed, ref, useId } from "vue";
import {
  ImagePlus,
  ArrowUp,
  ArrowDown,
  X,
  LoaderCircle,
  MoreHorizontal,
  Star,
  Pencil,
} from "@lucide/vue";
import { cn } from "@/lib/utils";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
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
const selectedId = ref<string | null>(null);
const selectedImage = computed(() =>
  gallery.value.images.find((image) => image.id === selectedId.value),
);
const orderedImages = computed(() => {
  const images = gallery.value.images;
  const primary =
    images.find((image) => image.id === gallery.value.primary_image_id) ??
    images[0];
  return primary
    ? [primary, ...images.filter((image) => image.id !== primary.id)]
    : [];
});
const error = computed(() => localError.value || props.validationError);
function move(index: number, delta: number): void {
  const images = [...orderedImages.value];
  const next = index + delta;
  if (index === 0 || next <= 0 || next >= images.length) return;
  const [image] = images.splice(index, 1);
  if (image) images.splice(next, 0, image);
  change({ ...gallery.value, images });
}
function remove(id: string): void {
  const images = gallery.value.images.filter((i) => i.id !== id);
  change({
    images,
    primary_image_id:
      orderedImages.value[0]?.id === id
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
    <FieldGroup class="gap-3">
      <Field :data-invalid="!!error || undefined">
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
          @change="upload"
        />
        <div
          class="grid min-w-0 grid-cols-3 gap-2"
          aria-label="Фотографии товара"
        >
          <div
            v-for="(image, index) in orderedImages"
            :key="image.id"
            :class="
              cn(
                'relative aspect-square min-w-0 overflow-hidden rounded-md border bg-muted',
                index === 0 && 'col-span-3',
              )
            "
          >
            <img
              :src="imageUrl(image.id)"
              :alt="image.alt"
              class="absolute inset-0 size-full object-contain"
              loading="lazy"
            />
            <Badge
              v-if="index === 0"
              variant="secondary"
              class="absolute bottom-2 left-2"
              >Главное</Badge
            >
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button
                  type="button"
                  variant="secondary"
                  size="icon-sm"
                  class="absolute top-1 right-1"
                  :disabled="pending"
                  :aria-label="`Действия с изображением ${index + 1}`"
                  ><MoreHorizontal
                /></Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuGroup>
                  <DropdownMenuItem
                    v-if="index !== 0"
                    :disabled="pending"
                    @select="change({ ...gallery, primary_image_id: image.id })"
                    ><Star />Сделать главным</DropdownMenuItem
                  >
                  <DropdownMenuItem
                    :disabled="pending"
                    @select="selectedId = image.id"
                    ><Pencil />Описание и подпись</DropdownMenuItem
                  >
                  <DropdownMenuItem
                    v-if="index !== 0"
                    :disabled="pending || index === 1"
                    @select="move(index, -1)"
                    ><ArrowUp />Переместить раньше</DropdownMenuItem
                  >
                  <DropdownMenuItem
                    v-if="index !== 0"
                    :disabled="pending || index === orderedImages.length - 1"
                    @select="move(index, 1)"
                    ><ArrowDown />Переместить позже</DropdownMenuItem
                  >
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem
                    variant="destructive"
                    :disabled="pending"
                    @select="remove(image.id)"
                    ><X />Убрать изображение</DropdownMenuItem
                  >
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <Button
            type="button"
            variant="outline"
            :class="
              cn(
                'aspect-square h-auto w-full flex-col gap-1 whitespace-normal border-dashed p-2',
                !orderedImages.length && 'col-span-3',
              )
            "
            :disabled="pending || gallery.images.length >= 100"
            aria-label="Загрузить изображение"
            :aria-busy="uploading"
            :aria-describedby="`${fileId}-hint ${error ? `${fileId}-error` : ''}`"
            @click="fileInput?.click()"
            ><LoaderCircle v-if="uploading" class="animate-spin" />
            <ImagePlus v-else />
            <span>{{ uploading ? "Загрузка…" : "Добавить фото" }}</span>
          </Button>
        </div>
        <FieldDescription :id="`${fileId}-hint`"
          >{{ productImageFormats }} · до 10 МБ ·
          {{ gallery.images.length }}/100</FieldDescription
        > </Field
      ><ProductFieldError :id="`${fileId}-error`" :error="error" />
    </FieldGroup>
  </fieldset>
  <Dialog :open="!!selectedImage" @update:open="!$event && (selectedId = null)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Описание изображения</DialogTitle>
        <DialogDescription
          >Описание помогает понять содержимое фото. Подпись поясняет его в
          галерее. Изменения сохраняются автоматически.</DialogDescription
        >
      </DialogHeader>
      <FieldGroup v-if="selectedImage">
        <Field>
          <FieldLabel :for="`${fileId}-alt`">Описание изображения</FieldLabel>
          <Input
            :id="`${fileId}-alt`"
            :model-value="selectedImage.alt"
            :disabled="pending"
            @update:model-value="text(selectedImage.id, 'alt', String($event))"
          />
        </Field>
        <Field>
          <FieldLabel :for="`${fileId}-caption`">Подпись</FieldLabel>
          <Input
            :id="`${fileId}-caption`"
            :model-value="selectedImage.caption"
            :disabled="pending"
            @update:model-value="
              text(selectedImage.id, 'caption', String($event))
            "
          />
        </Field>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="outline" @click="selectedId = null"
          >Закрыть</Button
        >
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
