<script setup lang="ts">
import { computed } from "vue";
import PublicationThumbnail from "../PublicationThumbnail.vue";
import type { BindingPosition } from "../../model/bindings/binding.types";
const props = defineProps<{ position: BindingPosition }>();
const labels: Record<string, string> = {
  in_stock: "В наличии",
  out_of_stock: "Нет в наличии",
  on_backorder: "Предзаказ",
  available: "В наличии",
  not_available: "Нет в наличии",
};
const image = computed(() => {
  const value = props.position.imageUrl;
  if (!value) return null;
  if (/^\/api\/console\/catalog\/items\//.test(value)) return value;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
});
</script>
<template>
  <div class="flex min-w-0 gap-3">
    <PublicationThumbnail :src="image" class="size-10 shrink-0" />
    <div class="min-w-0">
      <p class="break-words font-medium">
        {{ position.title ?? "Название отсутствует" }}
      </p>
      <p
        v-if="position.externalId"
        class="text-muted-foreground break-all text-xs"
      >
        ID площадки: {{ position.externalId }}
      </p>
      <p class="text-muted-foreground text-xs">
        {{ position.sku ?? position.externalId ?? position.id
        }}<span v-if="position.status === 'archived'"> · Архивный</span>
      </p>
      <p class="text-muted-foreground text-xs">
        {{
          position.price === null
            ? "Цена неизвестна"
            : `${position.price} ${position.currency ?? ""}`
        }}
        ·
        {{
          position.quantity === null
            ? position.availability
              ? (labels[position.availability] ?? position.availability)
              : "Наличие неизвестно"
            : `Остаток: ${position.quantity}`
        }}
      </p>
      <p
        v-if="position.stockSourceId !== position.id"
        class="text-muted-foreground text-xs"
      >
        Остаток родителя
      </p>
      <p v-if="position.stale" class="text-muted-foreground text-xs">
        Снимок предыдущей конфигурации
      </p>
    </div>
  </div>
</template>
