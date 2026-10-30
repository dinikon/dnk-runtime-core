<script setup lang="ts">
import { useId } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { CatalogContentEditor } from "@/modules/catalog";
import type {
  LocalizedOverrides,
  RepresentationContent,
  RepresentationImage,
} from "../../model/representation.types";

const props = defineProps<{
  value: LocalizedOverrides;
  inherited?: RepresentationContent;
  disabled: boolean;
  inactive: boolean;
}>();
const emit = defineEmits<{
  update: [value: LocalizedOverrides];
  pickImages: [];
}>();
const id = useId();
function gallery(value: RepresentationImage[]): void {
  emit("update", { ...props.value, gallery: value });
}
function updateImage(
  index: number,
  fields: Partial<RepresentationImage>,
): void {
  gallery(
    (props.value.gallery ?? []).map((image, position) =>
      position === index ? { ...image, ...fields } : { ...image },
    ),
  );
}
function moveImage(index: number, direction: number): void {
  const images = (props.value.gallery ?? []).map((image) => ({ ...image }));
  const target = index + direction;
  if (target < 0 || target >= images.length) return;
  [images[index], images[target]] = [images[target]!, images[index]!];
  gallery(images);
}
</script>

<template>
  <div class="min-w-0 space-y-6">
    <p v-if="inactive" class="text-sm text-muted-foreground">
      Язык отключён в настройках канала. Прежние значения сохраняются; их можно
      сбросить.
    </p>
    <fieldset :disabled="disabled || inactive" class="min-w-0 space-y-3">
      <label class="flex items-center gap-2 text-sm font-medium"
        ><Checkbox
          :model-value="value.title != null"
          @update:model-value="
            emit('update', {
              ...value,
              title: $event === true ? (inherited?.title ?? '') : undefined,
            })
          "
        />Переопределить название</label
      >
      <label :for="`${id}-title`" class="sr-only">Название для площадки</label>
      <Input
        :id="`${id}-title`"
        :model-value="value.title ?? ''"
        :placeholder="inherited?.title ?? 'Название для площадки'"
        :disabled="value.title == null || disabled || inactive"
        @update:model-value="
          emit('update', { ...value, title: String($event) })
        "
      />
      <p
        v-if="value.title != null && !value.title.trim()"
        role="alert"
        class="text-sm text-destructive"
      >
        Название не может быть пустым.
      </p>
    </fieldset>
    <fieldset :disabled="disabled || inactive" class="min-w-0 space-y-3">
      <label class="flex items-center gap-2 text-sm font-medium"
        ><Checkbox
          :model-value="value.body != null"
          @update:model-value="
            emit('update', {
              ...value,
              body: $event === true ? (inherited?.body ?? '') : undefined,
            })
          "
        />Переопределить описание</label
      >
      <CatalogContentEditor
        :model-value="value.body ?? ''"
        label="Описание для площадки"
        :disabled="value.body == null || disabled || inactive"
        @update:model-value="emit('update', { ...value, body: $event })"
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="disabled || inactive"
        @click="emit('update', { ...value, body: '' })"
        >Очистить описание</Button
      >
    </fieldset>
    <fieldset :disabled="disabled || inactive" class="min-w-0 space-y-3">
      <label class="flex items-center gap-2 text-sm font-medium"
        ><Checkbox
          :model-value="value.gallery != null"
          @update:model-value="
            emit('update', {
              ...value,
              gallery:
                $event === true
                  ? (inherited?.gallery ?? []).map((image) => ({ ...image }))
                  : undefined,
            })
          "
        />Переопределить галерею</label
      >
      <p class="text-sm text-muted-foreground">
        Галерея заменяется целиком. Первое изображение — главное.
      </p>
      <div v-if="value.gallery != null" class="space-y-3">
        <div
          v-for="(image, index) in value.gallery"
          :key="image.fileId"
          class="min-w-0 space-y-2 rounded-md border p-3"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-sm font-medium"
              >Изображение {{ index + 1
              }}{{ index === 0 ? " · Главное" : "" }}</span
            >
            <div class="flex gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                :aria-label="`Поднять изображение ${index + 1}`"
                :disabled="disabled || inactive || index === 0"
                @click="moveImage(index, -1)"
                >↑</Button
              ><Button
                type="button"
                variant="ghost"
                size="sm"
                :aria-label="`Опустить изображение ${index + 1}`"
                :disabled="
                  disabled || inactive || index === value.gallery.length - 1
                "
                @click="moveImage(index, 1)"
                >↓</Button
              ><Button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="disabled || inactive"
                @click="
                  gallery(
                    value.gallery.filter((_, position) => position !== index),
                  )
                "
                >Убрать</Button
              >
            </div>
          </div>
          <label
            :for="`${id}-alt-${index}`"
            class="block text-xs text-muted-foreground"
            >Альтернативный текст</label
          ><Input
            :id="`${id}-alt-${index}`"
            :model-value="image.alt"
            @update:model-value="updateImage(index, { alt: String($event) })"
          />
          <label
            :for="`${id}-caption-${index}`"
            class="block text-xs text-muted-foreground"
            >Подпись</label
          ><Input
            :id="`${id}-caption-${index}`"
            :model-value="image.caption"
            @update:model-value="
              updateImage(index, { caption: String($event) })
            "
          />
        </div>
        <p v-if="!value.gallery.length" class="text-sm text-muted-foreground">
          Пустая галерея: изображения будут удалены из представления.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="disabled || inactive"
          @click="emit('pickImages')"
          >Выбрать изображения</Button
        ><Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="disabled || inactive"
          @click="gallery([])"
          >Очистить галерею</Button
        >
      </div>
    </fieldset>
    <Button
      type="button"
      variant="outline"
      size="sm"
      :disabled="disabled"
      @click="emit('update', {})"
      >Сбросить поля к наследованию</Button
    >
  </div>
</template>
