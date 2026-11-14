<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { StockLot } from "../../model/stock-lot.types";
import { displayStockDate } from "../../model/stock-lot.validation";
defineProps<{
  search: string;
  items: readonly StockLot[];
  selectedId: string;
  selected?: StockLot;
  selectedError: string;
  loading: boolean;
  busy: boolean;
  hasMore: boolean;
  error: string;
  disabled: boolean;
}>();
const emit = defineEmits<{
  search: [value: string];
  select: [id: string];
  more: [];
  retry: [];
  retrySelected: [];
  lots: [];
}>();
</script>
<template>
  <section class="flex min-w-0 flex-col gap-3" aria-label="Выбор партии">
    <div v-if="selectedId" class="rounded-md border p-3 text-sm">
      <template v-if="selected"
        ><p class="break-all">
          Выбрана партия:
          <strong class="font-mono">{{ selected.number }}</strong>
        </p>
        <p>
          Производство: {{ displayStockDate(selected.manufacturedOn) }} · Срок:
          {{ displayStockDate(selected.expiresOn) }}
        </p>
        <p class="text-muted-foreground">
          Источник дат — связанная партия. Даты изменяются в её карточке.
        </p></template
      >
      <template v-else
        ><p role="status">
          {{ selectedError || "Загрузка выбранной партии…" }}
        </p>
        <Button
          v-if="selectedError"
          type="button"
          variant="outline"
          :disabled="disabled"
          @click="emit('retrySelected')"
          >Повторить загрузку партии</Button
        ></template
      >
      <Button
        type="button"
        variant="link"
        :disabled="disabled"
        @click="emit('select', '')"
        >Очистить выбор</Button
      >
    </div>
    <label for="serial-lot-search" class="text-sm font-medium"
      >Поиск партии на сервере</label
    >
    <Input
      id="serial-lot-search"
      :model-value="search"
      :disabled="disabled"
      placeholder="Номер партии"
      autocomplete="off"
      @update:model-value="emit('search', String($event))"
      @keydown.enter.prevent
    />
    <p v-if="error" role="alert" class="text-sm text-destructive">
      {{ error }}
      <Button
        type="button"
        variant="link"
        :disabled="disabled || busy"
        @click="emit('retry')"
        >Повторить</Button
      >
    </p>
    <p
      v-if="loading || busy"
      role="status"
      class="text-sm text-muted-foreground"
    >
      Загрузка партий…
    </p>
    <ul
      v-if="items.length"
      class="max-h-48 space-y-2 overflow-y-auto"
      aria-label="Найденные партии"
    >
      <li v-for="lot in items" :key="lot.id">
        <Button
          type="button"
          variant="outline"
          class="h-auto w-full justify-start whitespace-normal p-3 text-left"
          :disabled="disabled"
          :aria-pressed="selectedId === lot.id"
          @click="emit('select', lot.id)"
          ><span class="min-w-0"
            ><span class="block break-all font-mono"
              >{{ selectedId === lot.id ? "✓ " : "" }}{{ lot.number }}</span
            ><span class="block text-xs text-muted-foreground"
              >Производство: {{ displayStockDate(lot.manufacturedOn) }} · Срок:
              {{ displayStockDate(lot.expiresOn) }}</span
            ></span
          ></Button
        >
      </li>
    </ul>
    <p
      v-else-if="!loading && !busy && !error"
      class="text-sm text-muted-foreground"
    >
      Партии не найдены. Измените поиск или создайте партию в разделе партий.
    </p>
    <Button
      v-if="hasMore"
      type="button"
      variant="outline"
      :disabled="disabled || busy"
      @click="emit('more')"
      >Загрузить ещё партии</Button
    >
    <Button
      type="button"
      variant="link"
      :disabled="disabled"
      @click="emit('lots')"
      >Открыть раздел партий</Button
    >
  </section>
</template>
