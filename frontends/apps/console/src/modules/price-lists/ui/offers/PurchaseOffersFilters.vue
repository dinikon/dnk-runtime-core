<script setup lang="ts">
import { FilterX, Search } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { OfferFilters, PriceList } from "../../model/types";

defineProps<{
  filters: OfferFilters;
  priceLists: PriceList[];
  hasFilters: boolean;
  rangeError: boolean;
}>();
const emit = defineEmits<{
  setFilter: [key: keyof OfferFilters, value: string, immediate: boolean];
  reset: [];
}>();

function selectValue(key: "priceListId" | "availability" | "hasRrp", value: unknown) {
  emit("setFilter", key, value === "all" ? "" : String(value ?? ""), true);
}
</script>

<template>
  <section class="grid shrink-0 gap-3 rounded-lg border bg-muted/30 p-3 lg:grid-cols-[minmax(220px,2fr)_1fr_repeat(3,minmax(150px,1fr))_auto]">
    <label class="relative">
      <span class="sr-only">Поиск</span><Search class="absolute left-3 top-2.5 size-4 text-muted-foreground" />
      <Input :model-value="filters.q" class="pl-9" placeholder="Название, SKU или внешний ID" @update:model-value="emit('setFilter', 'q', String($event ?? ''), false)" />
    </label>
    <Select :model-value="filters.priceListId || 'all'" @update:model-value="selectValue('priceListId', $event)">
      <SelectTrigger><SelectValue placeholder="Все прайс-листы" /></SelectTrigger>
      <SelectContent><SelectItem value="all">Все прайс-листы</SelectItem><SelectItem v-for="list in priceLists" :key="list.id" :value="list.id">{{ list.title }}</SelectItem></SelectContent>
    </Select>
    <div class="flex gap-1"><Input :model-value="filters.purchasePriceMin" type="number" min="0" placeholder="Цена от" @update:model-value="emit('setFilter', 'purchasePriceMin', String($event ?? ''), true)" /><Input :model-value="filters.purchasePriceMax" type="number" min="0" placeholder="до" @update:model-value="emit('setFilter', 'purchasePriceMax', String($event ?? ''), true)" /></div>
    <div class="flex gap-1"><Input :model-value="filters.incomeMin" type="number" placeholder="РРД от" @update:model-value="emit('setFilter', 'incomeMin', String($event ?? ''), true)" /><Input :model-value="filters.incomeMax" type="number" placeholder="до" @update:model-value="emit('setFilter', 'incomeMax', String($event ?? ''), true)" /></div>
    <div class="flex gap-1"><Input :model-value="filters.marginMin" type="number" placeholder="Маржа от, %" @update:model-value="emit('setFilter', 'marginMin', String($event ?? ''), true)" /><Input :model-value="filters.marginMax" type="number" placeholder="до" @update:model-value="emit('setFilter', 'marginMax', String($event ?? ''), true)" /></div>
    <div class="flex gap-2">
      <Select :model-value="filters.availability || 'all'" @update:model-value="selectValue('availability', $event)"><SelectTrigger class="min-w-36"><SelectValue placeholder="Наличие" /></SelectTrigger><SelectContent><SelectItem value="all">Любое</SelectItem><SelectItem value="in_stock">В наличии</SelectItem><SelectItem value="out_of_stock">Нет в наличии</SelectItem><SelectItem value="unknown">Неизвестно</SelectItem></SelectContent></Select>
      <Select :model-value="filters.hasRrp || 'all'" @update:model-value="selectValue('hasRrp', $event)"><SelectTrigger class="min-w-32"><SelectValue placeholder="РРЦ" /></SelectTrigger><SelectContent><SelectItem value="all">Любая РРЦ</SelectItem><SelectItem value="true">Только с РРЦ</SelectItem><SelectItem value="false">Без РРЦ</SelectItem></SelectContent></Select>
      <Button variant="outline" size="icon" :disabled="!hasFilters" aria-label="Сбросить фильтры" @click="emit('reset')"><FilterX /></Button>
    </div>
  </section>
  <p v-if="rangeError" class="shrink-0 text-sm text-destructive">Значение «от» не может быть больше значения «до».</p>
</template>
