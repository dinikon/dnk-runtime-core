<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import type { ContentDelivery } from "../../model/content-delivery.types";
import {
  contentDeliveryStatus,
  contentDeliverySummary,
} from "../../model/content-delivery.display";

defineProps<{
  items: ContentDelivery[];
  loading: boolean;
  error: string;
  busy: boolean;
  canRequest: boolean;
  canReview: boolean;
  reviewed: boolean;
  fingerprint: string;
  issues: string[];
  errorMessages: Record<string, string>;
}>();
const emit = defineEmits<{
  request: [];
  reconcile: [item: ContentDelivery];
  refresh: [];
  review: [checked: boolean];
}>();
</script>

<template>
  <section class="space-y-3 border-t pt-4" aria-label="Доставка контента">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-sm font-semibold">Обновление WooCommerce</h3>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        :disabled="loading || busy"
        @click="emit('refresh')"
        >Перечитать результат</Button
      >
    </div>
    <p class="text-sm text-muted-foreground">
      {{ contentDeliverySummary(items) }}
    </p>
    <p class="text-xs text-muted-foreground">
      Обновляются название, описание и изображения. Название вариации формирует
      площадка из товара и атрибутов.
    </p>
    <ul v-if="issues.length" class="space-y-1 text-sm text-destructive">
      <li v-for="issue in issues" :key="issue">{{ issue }}</li>
    </ul>
    <label class="flex items-start gap-2 text-sm">
      <input
        type="checkbox"
        class="mt-1"
        :checked="reviewed"
        :disabled="!canReview || busy"
        @change="emit('review', ($event.target as HTMLInputElement).checked)"
      />
      <span>Я проверил preview сохранённого представления.</span>
    </label>
    <Button
      type="button"
      :disabled="!canRequest || busy"
      @click="emit('request')"
      >{{ busy ? "Выполняем…" : "Обновить на площадке" }}</Button
    >
    <Alert v-if="error" variant="destructive"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <Skeleton v-if="loading && !items.length" class="h-20 w-full" />
    <ul v-else class="space-y-2">
      <li
        v-for="item in items"
        :key="item.publicationId"
        class="space-y-1 rounded-md border p-3 text-sm"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="font-medium"
            >{{
              item.role === "container"
                ? "Контейнер"
                : item.publicationKind === "variant"
                  ? "Вариация"
                  : "Товар"
            }}
            · {{ item.externalId }}</span
          ><span>{{ contentDeliveryStatus(item.status) }}</span>
        </div>
        <p class="text-xs text-muted-foreground">
          Запрошено: {{ item.requestedGeneration }} · Применено:
          {{ item.appliedGeneration ?? "—" }}
        </p>
        <p v-if="item.completedAt" class="text-xs text-muted-foreground">
          Последний результат:
          {{ new Date(item.completedAt).toLocaleString("ru-RU") }}
        </p>
        <p
          v-if="item.contentFingerprint !== fingerprint"
          class="text-xs text-muted-foreground"
        >
          Результат относится к прежнему контенту.
        </p>
        <p
          v-if="errorMessages[item.publicationId]"
          class="text-sm text-destructive"
        >
          {{ errorMessages[item.publicationId] }}
        </p>
        <p
          v-if="item.recoveryRequired && item.status === 'queued'"
          class="text-xs text-muted-foreground"
        >
          Задание прервано. Повторный запуск восстановит его.
        </p>
        <Button
          v-if="
            item.status === 'unknown' ||
            (item.status === 'in_flight' && item.recoveryRequired)
          "
          type="button"
          size="sm"
          variant="outline"
          :disabled="busy || !item.recoveryRequired"
          @click="emit('reconcile', item)"
          >Сверить с площадкой</Button
        >
      </li>
    </ul>
  </section>
</template>
