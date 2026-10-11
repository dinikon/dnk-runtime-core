<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { clone } from "../../model/clone";
import type { GalleryDTO } from "../../api/catalog.dto";
const props = defineProps<{
  own: GalleryDTO | null;
  effective: GalleryDTO | null;
  pending: boolean;
  reset: number;
  variant: boolean;
  imageUrl: (id: string) => string;
}>();
const emit = defineEmits<{
  save: [gallery: GalleryDTO];
  inherit: [];
  upload: [file: File, main: boolean];
  dirty: [value: boolean];
}>();
const gallery = ref<GalleryDTO>({ images: [], primary_image_id: null }),
  dirty = ref(false);
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
function resetFields() {
  gallery.value = clone(
    props.own ?? props.effective ?? { images: [], primary_image_id: null },
  );
  dirty.value = false;
  emit("dirty", false);
}
resetFields();
watch(() => props.reset, resetFields);
watch(
  () => props.own,
  () => {
    if (!dirty.value) resetFields();
  },
);
function copy() {
  const ids = new Map(
    gallery.value.images.map((i) => [i.id, crypto.randomUUID()]),
  );
  emit("save", {
    images: gallery.value.images.map((i) => ({ ...i, id: ids.get(i.id)! })),
    primary_image_id: gallery.value.primary_image_id
      ? (ids.get(gallery.value.primary_image_id) ?? null)
      : null,
  });
}
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
  <div class="space-y-4">
    <p v-if="variant && !own" class="break-words text-sm text-muted-foreground">
      Галерея наследуется от родителя в выбранном языке.
    </p>
    <div v-if="variant && !own" class="flex flex-wrap gap-3">
      <figure v-for="image in gallery.images" :key="image.id" class="space-y-1">
        <img
          :src="imageUrl(image.id)"
          :alt="image.alt"
          class="h-24 w-24 rounded object-cover"
        />
        <figcaption class="break-words text-sm text-muted-foreground">
          {{
            image.id === gallery.primary_image_id ? "Главное" : image.caption
          }}
        </figcaption>
      </figure>
    </div>
    <div v-if="variant && !own" class="flex flex-wrap gap-2">
      <Button variant="outline" :disabled="pending" @click="copy"
        >Создать свою копию галереи</Button
      ><Button
        variant="outline"
        :disabled="pending"
        @click="emit('save', { images: [], primary_image_id: null })"
        >Скрыть изображения</Button
      >
    </div>
    <form
      v-else
      class="space-y-4"
      @submit.prevent="
        emit('save', {
          ...gallery,
          images: gallery.images.map((i, position) => ({ ...i, position })),
        })
      "
    >
      <fieldset :disabled="pending" class="space-y-3">
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
          <div class="min-w-0 flex-1 space-y-2">
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
          ><Button
            v-if="variant"
            type="button"
            variant="outline"
            @click="emit('inherit')"
            >Наследовать</Button
          >
        </div>
      </fieldset>
    </form>
  </div>
</template>
