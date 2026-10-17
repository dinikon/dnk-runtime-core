<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { clone } from "../../model/clone";
import type { ProductGallery } from "../../model/product.types";
const props = defineProps<{
  value: ProductGallery | null;
  pending: boolean;
  reset: number;
  imageUrl: (id: string) => string;
}>();
const emit = defineEmits<{
  save: [gallery: ProductGallery];
  upload: [file: File, main: boolean];
  dirty: [value: boolean];
}>();
const gallery = ref<ProductGallery>({ images: [], primary_image_id: null }),
  dirty = ref(false);
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
function resetFields() {
  gallery.value = clone(props.value ?? { images: [], primary_image_id: null });
  dirty.value = false;
  emit("dirty", false);
}
resetFields();
watch(() => props.reset, resetFields);
watch(
  () => props.value,
  () => {
    if (!dirty.value) resetFields();
  },
);
function move(index: number, delta: number) {
  const next = index + delta;
  if (next < 0 || next >= gallery.value.images.length) return;
  const [image] = gallery.value.images.splice(index, 1);
  if (image) gallery.value.images.splice(next, 0, image);
  mark();
}
function remove(id: string) {
  gallery.value.images = gallery.value.images.filter((i) => i.id !== id);
  if (gallery.value.primary_image_id === id)
    gallery.value.primary_image_id = gallery.value.images[0]?.id ?? null;
  mark();
}
function upload(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (file) emit("upload", file, !gallery.value.images.length);
  target.value = "";
}
</script>
<template>
  <div class="flex flex-col gap-4">
    <form
      class="flex flex-col gap-4"
      @submit.prevent="
        emit('save', {
          ...gallery,
          images: gallery.images.map((i, position) => ({ ...i, position })),
        })
      "
    >
      <fieldset :disabled="pending" class="flex flex-col gap-3">
        <div
          v-for="(image, index) in gallery.images"
          :key="image.id"
          class="flex flex-wrap gap-3 rounded border p-3"
        >
          <img
            :src="imageUrl(image.id)"
            :alt="image.alt"
            class="h-24 w-24 rounded object-cover"
          />
          <div class="min-w-0 flex-1 flex flex-col gap-2">
            <label
              ><input
                v-model="gallery.primary_image_id"
                type="radio"
                :value="image.id"
                @change="mark"
              />
              Главное изображение</label
            ><input
              v-model="image.alt"
              aria-label="Alt изображения"
              placeholder="Описание изображения"
              class="block w-full rounded border bg-background p-2"
              @input="mark"
            /><input
              v-model="image.caption"
              aria-label="Подпись изображения"
              placeholder="Подпись"
              class="block w-full rounded border bg-background p-2"
              @input="mark"
            />
            <div class="flex flex-wrap gap-2">
              <Button type="button" variant="ghost" @click="move(index, -1)"
                >Выше</Button
              ><Button type="button" variant="ghost" @click="move(index, 1)"
                >Ниже</Button
              ><Button type="button" variant="ghost" @click="remove(image.id)"
                >Убрать</Button
              >
            </div>
          </div>
        </div>
        <p
          v-if="!gallery.images.length"
          class="break-words text-sm text-muted-foreground"
        >
          Галерея пуста.
        </p>
        <label class="block"
          >Загрузить изображение<input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            :disabled="dirty"
            class="block mt-2 w-full min-w-0"
            @change="upload"
        /></label>
        <p v-if="dirty" class="text-sm">Сохраните порядок перед загрузкой.</p>
        <div class="flex flex-wrap gap-2">
          <Button type="submit">Сохранить галерею</Button
          ><Button type="button" variant="outline" @click="resetFields"
            >Отмена</Button
          >
        </div>
      </fieldset>
    </form>
  </div>
</template>
