<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  StockFilters,
  StockReadKind,
  StockFilterKind,
} from "../../model/stock-accounting.types";
import {
  stockFilterNames,
  stockFilterKeys,
} from "../../model/stock-accounting-navigation";
defineProps<{
  filters: StockFilters;
  kind: StockReadKind;
  search: string;
  labels: Record<string, string>;
}>();
const emit = defineEmits<{
  patch: [value: Partial<StockFilters>];
  search: [value: string];
  pick: [kind: StockFilterKind];
  reset: [];
}>();
function period(event: Event, key: "postedFrom" | "postedTo"): void {
  const value = (event.target as HTMLInputElement).value;
  emit("patch", { [key]: value ? value + "T00:00:00Z" : undefined });
}
</script>
<template>
  <section
    class="flex shrink-0 flex-col gap-3 rounded-lg border p-4"
    aria-label="Фильтры учёта"
  >
    <label class="text-sm"
      >Поиск по SKU, партии или серии<Input
        :model-value="search"
        type="search"
        maxlength="128"
        @update:model-value="emit('search', String($event))"
    /></label>
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="(label, key) in stockFilterNames"
        :key="key"
        class="flex min-w-0 flex-col gap-1"
      >
        <span class="text-sm">{{ label }}</span>
        <div class="flex gap-1">
          <Button
            variant="outline"
            class="min-w-0 flex-1 justify-start truncate"
            :disabled="
              (key === 'locationId' && !filters.warehouseId) ||
              ((key === 'lotId' || key === 'serialId') &&
                !filters.inventoryItemId)
            "
            :aria-label="'Выбрать фильтр: ' + label"
            @click="emit('pick', key)"
            >{{
              filters[key]
                ? labels[stockFilterKeys[key] + "_label"] || filters[key]
                : "Все"
            }}</Button
          ><Button
            v-if="filters[key]"
            variant="ghost"
            :aria-label="'Сбросить фильтр: ' + label"
            @click="emit('patch', { [key]: undefined })"
            >×</Button
          >
        </div>
      </div>
      <label class="text-sm"
        >Состояние запаса<select
          class="mt-1 h-9 w-full rounded-md border bg-background px-2"
          :value="filters.stockStatus ?? ''"
          @change="
            emit('patch', {
              stockStatus:
                ($event.target as HTMLSelectElement).value || undefined,
            })
          "
        >
          <option value="">Все</option>
          <option value="SELLABLE">Пригодный к продаже</option>
          <option value="QUARANTINE">Карантин</option>
          <option value="DAMAGED">Повреждённый</option>
          <option value="BLOCKED">Заблокированный</option>
        </select></label
      >
      <template v-if="kind !== 'positions'"
        ><label class="text-sm"
          >Вид операции<select
            class="mt-1 h-9 w-full rounded-md border bg-background px-2"
            :value="filters.operationType ?? ''"
            @change="
              emit('patch', {
                operationType:
                  ($event.target as HTMLSelectElement).value || undefined,
              })
            "
          >
            <option value="">Все</option>
            <option value="RECEIPT">Поступление</option>
            <option value="ISSUE">Расход</option>
            <option value="WRITE_OFF">Списание</option>
            <option value="RETURN">Возврат</option>
            <option value="STATUS_CHANGE">Изменение состояния</option>
            <option value="INTERNAL_MOVE">Перемещение</option>
            <option value="ADJUSTMENT">Корректировка</option>
          </select></label
        ><label class="text-sm"
          >С даты (UTC)<Input
            type="date"
            :model-value="filters.postedFrom?.slice(0, 10) ?? ''"
            @change="period($event, 'postedFrom')"
            @input="period($event, 'postedFrom')" /></label
        ><label class="text-sm"
          >До даты, не включая (UTC)<Input
            type="date"
            :model-value="filters.postedTo?.slice(0, 10) ?? ''"
            @change="period($event, 'postedTo')"
            @input="period($event, 'postedTo')" /></label
      ></template>
    </div>
    <p class="text-xs text-muted-foreground">
      Для выбора локации сначала выберите склад; для партии или серии — SKU.
    </p>
    <label v-if="kind === 'positions'" class="flex items-center gap-2 text-sm"
      ><input
        type="checkbox"
        :checked="filters.includeZero ?? false"
        @change="
          emit('patch', {
            includeZero: ($event.target as HTMLInputElement).checked,
          })
        "
      />Показать нулевые позиции</label
    >
    <div class="flex flex-wrap items-center gap-2">
      <span
        v-for="key in [
          'positionId',
          'documentId',
          'executionId',
          'postingId',
        ] as const"
        :key="key"
        class="text-xs"
        ><Button
          v-if="filters[key]"
          variant="outline"
          size="sm"
          @click="emit('patch', { [key]: undefined })"
          >{{ key }}: {{ filters[key] }} ×</Button
        ></span
      ><Button variant="ghost" class="self-start" @click="emit('reset')"
        >Сбросить фильтры</Button
      >
    </div>
  </section>
</template>
