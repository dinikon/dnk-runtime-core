<script setup lang="ts">
import { ref, watch } from "vue";
import { Image } from "@lucide/vue";
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import type { ProductOverviewModel } from "../../model/product.types";
const props = defineProps<{
  images: ProductOverviewModel["images"];
  primary: string | null;
}>();
const selected = ref("");
watch(
  () => [props.images, props.primary],
  () => {
    selected.value = props.primary ?? props.images[0]?.id ?? "";
  },
  { immediate: true },
);
</script>
<template>
  <div class="flex min-w-0 flex-col gap-4">
    <figure
      v-if="images.length"
      class="overflow-hidden rounded-xl border bg-muted/20"
    >
      <img
        :src="images.find((i) => i.id === selected)?.url ?? images[0]?.url"
        :alt="images.find((i) => i.id === selected)?.alt ?? ''"
        class="aspect-[16/10] w-full object-contain"
      />
      <figcaption
        v-if="images.find((i) => i.id === selected)?.caption"
        class="px-4 pb-4 text-sm text-muted-foreground"
      >
        {{ images.find((i) => i.id === selected)?.caption }}
      </figcaption>
    </figure>
    <Empty v-else class="aspect-[16/10] rounded-xl border bg-muted/20"
      ><EmptyHeader
        ><EmptyMedia variant="icon"><Image /></EmptyMedia
        ><EmptyTitle>Изображения не добавлены</EmptyTitle
        ><EmptyDescription
          >Добавьте фотографии в редакторе товара.</EmptyDescription
        ></EmptyHeader
      ></Empty
    >
    <div
      v-if="images.length > 1"
      class="flex flex-wrap gap-3"
      aria-label="Галерея товара"
    >
      <button
        v-for="(image, index) in images"
        :key="image.id"
        type="button"
        class="size-20 overflow-hidden rounded-lg border-2 bg-muted/20 outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :class="selected === image.id ? 'border-primary' : 'border-transparent'"
        :aria-label="`Изображение ${index + 1}`"
        :aria-pressed="selected === image.id"
        @click="selected = image.id"
      >
        <img :src="image.url" :alt="image.alt" class="size-full object-cover" />
      </button>
    </div>
  </div>
</template>
