<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { publicationStatusLabel } from "../../model/feed-publication.errors";
import type { Publication } from "../../model/feed-publication.types";
defineProps<{
  items: Publication[];
  busy: boolean;
  readonly: boolean;
  selectedId: string;
}>();
const emit = defineEmits<{
  open: [value: Publication];
  pause: [value: Publication];
  enable: [value: Publication];
  archive: [value: Publication];
  restore: [value: Publication];
}>();
</script>
<template>
  <div class="flex min-w-0 flex-col gap-3">
    <article
      v-for="item in items"
      :key="item.id"
      class="flex min-w-0 flex-wrap items-center justify-between gap-4 rounded-lg border p-4"
      :class="selectedId === item.id ? 'border-ring' : ''"
    >
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="break-words text-left font-medium underline-offset-4 hover:underline"
            :disabled="busy"
            @click="emit('open', item)"
          >
            {{ item.title ?? item.sku ?? "Позиция каталога" }}</button
          ><Badge variant="secondary">{{
            publicationStatusLabel(item.status)
          }}</Badge>
        </div>
        <p class="break-words text-sm text-muted-foreground">
          {{
            item.sku ??
            `Без SKU · ${(item.variantId ?? item.itemId).slice(0, 8)}`
          }}
          ·
          {{ item.variantId ? "Вариант" : "Простой товар" }}
        </p>
        <p
          v-if="item.parentTitle"
          class="break-words text-xs text-muted-foreground"
        >
          Карточка: {{ item.parentTitle }}
        </p>
        <p class="text-xs text-muted-foreground">
          Добавлен {{ new Date(item.createdAt).toLocaleDateString("ru-RU") }}
        </p>
        <p v-if="!item.sourceAvailable" class="text-sm text-destructive">
          Источник недоступен. Привязка сохранена.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="busy"
          @click="emit('open', item)"
          >Открыть</Button
        ><template v-if="!readonly"
          ><Button
            v-if="item.status === 'ENABLED'"
            type="button"
            variant="outline"
            :disabled="busy"
            @click="emit('pause', item)"
            >Приостановить</Button
          ><Button
            v-if="item.status === 'PAUSED' || item.status === 'DRAFT'"
            type="button"
            variant="outline"
            :disabled="busy"
            @click="emit('enable', item)"
            >Возобновить</Button
          ><Button
            v-if="item.status === 'ARCHIVED'"
            type="button"
            variant="outline"
            :disabled="busy || !item.sourceAvailable"
            @click="emit('restore', item)"
            >Вернуть в фид</Button
          ><Button
            v-else
            type="button"
            variant="outline"
            :disabled="busy"
            @click="emit('archive', item)"
            >Убрать из фида</Button
          ></template
        >
      </div>
    </article>
  </div>
</template>
