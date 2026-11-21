<script setup lang="ts">
import type { ReturnPreview } from "../../model/return-preview.types";
import { stockStatusLabel } from "../../model/stock-accounting.constants";
defineProps<{ preview: ReturnPreview }>();
</script>
<template>
  <section
    class="min-w-0 space-y-3 rounded-lg border p-4"
    aria-label="Предварительный результат"
  >
    <h2 class="text-lg font-semibold">Предварительный результат</h2>
    <p class="text-sm text-muted-foreground">
      Расчёт по текущему физическому количеству. Остаток не резервируется; при
      проведении он проверяется повторно.
    </p>
    <p class="whitespace-pre-wrap break-words text-sm">
      Причина: {{ preview.reason }}
    </p>
    <ul class="space-y-2 text-sm">
      <li
        v-for="(p, index) in preview.positions"
        :key="index"
        class="rounded border p-3"
      >
        <p class="font-medium">
          {{ p.role === "SOURCE" ? "Расход" : "Приход" }} · {{ p.sku }} ·
          {{ p.locationCode }} · {{ stockStatusLabel(p.stockStatus) }}
        </p>
        <p v-if="p.lotNumber || p.serialNumber">
          {{ p.lotNumber ? `Партия ${p.lotNumber}` : "" }}
          {{ p.serialNumber ? `Серия ${p.serialNumber}` : "" }}
        </p>
        <p>
          Было: {{ p.before }} · Изменение: {{ p.delta }} · Стало: {{ p.after }}
          {{ p.baseUom }}
        </p>
        <p v-if="!p.exists" class="text-xs text-muted-foreground">
          Новая позиция будет создана при проведении.
        </p>
      </li>
    </ul>
  </section>
</template>
