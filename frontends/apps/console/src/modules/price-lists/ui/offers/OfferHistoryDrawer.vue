<script setup lang="ts">
import { computed } from "vue";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, RotateCcw } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { OfferHistoryFilters, PartnerOffer, PartnerOfferState } from "../../model/types";
import { formatMoney } from "../../model/query-state";

const props = defineProps<{
  offer: PartnerOffer | null;
  items: PartnerOfferState[];
  filters: OfferHistoryFilters;
  total: number;
  pending: boolean;
  failed: boolean;
}>();
const emit = defineEmits<{
  close: [];
  setFilter: [key: keyof OfferHistoryFilters, value: string];
  sort: [field: string];
  page: [page: number];
  reset: [];
  retry: [];
}>();
const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.filters.limit)));
const sortIcon = (field: string) => props.filters.sort === field && props.filters.direction === "asc" ? ArrowUp : ArrowDown;
const reasonLabel: Record<string, string> = { initial: "Первая фиксация", source_change: "Изменение источника", reappeared: "Появился снова", missing_policy: "Правило отсутствия" };
const availabilityLabel: Record<string, string> = { in_stock: "В наличии", out_of_stock: "Нет в наличии", unknown: "Неизвестно" };
</script>

<template>
  <Sheet :open="offer !== null" @update:open="(open) => { if (!open) emit('close') }">
    <SheetContent class="flex w-full flex-col gap-5 overflow-hidden sm:max-w-6xl">
      <SheetHeader><SheetTitle>{{ offer?.title }}</SheetTitle><SheetDescription>{{ offer?.sku }} · {{ total }} изменений и версий состояния</SheetDescription></SheetHeader>
      <FieldGroup class="grid shrink-0 gap-3 border-y py-4 sm:grid-cols-2 xl:grid-cols-4">
        <Field><FieldLabel>Период</FieldLabel><div class="flex gap-2"><Input :model-value="filters.observedFrom" type="datetime-local" aria-label="Период от" @update:model-value="emit('setFilter', 'observedFrom', String($event ?? ''))" /><Input :model-value="filters.observedTo" type="datetime-local" aria-label="Период до" @update:model-value="emit('setFilter', 'observedTo', String($event ?? ''))" /></div></Field>
        <Field><FieldLabel>Закупочная цена</FieldLabel><div class="flex gap-2"><Input :model-value="filters.purchasePriceMin" type="number" min="0" placeholder="От" @update:model-value="emit('setFilter', 'purchasePriceMin', String($event ?? ''))" /><Input :model-value="filters.purchasePriceMax" type="number" min="0" placeholder="До" @update:model-value="emit('setFilter', 'purchasePriceMax', String($event ?? ''))" /></div></Field>
        <Field><FieldLabel>РРЦ</FieldLabel><div class="flex gap-2"><Input :model-value="filters.rrpMin" type="number" min="0" placeholder="От" @update:model-value="emit('setFilter', 'rrpMin', String($event ?? ''))" /><Input :model-value="filters.rrpMax" type="number" min="0" placeholder="До" @update:model-value="emit('setFilter', 'rrpMax', String($event ?? ''))" /></div></Field>
        <Field><FieldLabel>РРД</FieldLabel><div class="flex gap-2"><Input :model-value="filters.incomeMin" type="number" placeholder="От" @update:model-value="emit('setFilter', 'incomeMin', String($event ?? ''))" /><Input :model-value="filters.incomeMax" type="number" placeholder="До" @update:model-value="emit('setFilter', 'incomeMax', String($event ?? ''))" /></div></Field>
        <Field><FieldLabel>Маржа, %</FieldLabel><div class="flex gap-2"><Input :model-value="filters.marginMin" type="number" placeholder="От" @update:model-value="emit('setFilter', 'marginMin', String($event ?? ''))" /><Input :model-value="filters.marginMax" type="number" placeholder="До" @update:model-value="emit('setFilter', 'marginMax', String($event ?? ''))" /></div></Field>
        <Field><FieldLabel>Количество</FieldLabel><div class="flex gap-2"><Input :model-value="filters.quantityMin" type="number" min="0" placeholder="От" @update:model-value="emit('setFilter', 'quantityMin', String($event ?? ''))" /><Input :model-value="filters.quantityMax" type="number" min="0" placeholder="До" @update:model-value="emit('setFilter', 'quantityMax', String($event ?? ''))" /></div></Field>
        <Field><FieldLabel>Наличие</FieldLabel><Select :model-value="filters.availability || 'all'" @update:model-value="emit('setFilter', 'availability', $event === 'all' ? '' : String($event))"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">Любое</SelectItem><SelectItem value="in_stock">В наличии</SelectItem><SelectItem value="out_of_stock">Нет в наличии</SelectItem><SelectItem value="unknown">Неизвестно</SelectItem></SelectGroup></SelectContent></Select></Field>
        <Field><FieldLabel>Причина</FieldLabel><div class="flex gap-2"><Select :model-value="filters.changeReason || 'all'" @update:model-value="emit('setFilter', 'changeReason', $event === 'all' ? '' : String($event))"><SelectTrigger class="flex-1"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="all">Любая</SelectItem><SelectItem value="initial">Первая фиксация</SelectItem><SelectItem value="source_change">Изменение источника</SelectItem><SelectItem value="reappeared">Появился снова</SelectItem><SelectItem value="missing_policy">Правило отсутствия</SelectItem></SelectGroup></SelectContent></Select><Button type="button" variant="outline" size="icon" aria-label="Сбросить фильтры" @click="emit('reset')"><RotateCcw /></Button></div></Field>
      </FieldGroup>
      <div class="min-h-0 flex-1 overflow-auto rounded-lg border">
        <Table>
          <TableHeader class="sticky top-0 bg-background"><TableRow>
            <TableHead class="whitespace-nowrap"><button class="inline-flex items-center gap-1" @click="emit('sort', 'observed_at')">Дата<component :is="sortIcon('observed_at')" class="size-3" /></button></TableHead>
            <TableHead class="text-right"><button class="inline-flex items-center gap-1" @click="emit('sort', 'purchase_price')">Закупка<component :is="sortIcon('purchase_price')" class="size-3" /></button></TableHead>
            <TableHead class="text-right"><button class="inline-flex items-center gap-1" @click="emit('sort', 'rrp')">РРЦ<component :is="sortIcon('rrp')" class="size-3" /></button></TableHead>
            <TableHead class="text-right"><button class="inline-flex items-center gap-1" @click="emit('sort', 'recommended_retail_income')">РРД<component :is="sortIcon('recommended_retail_income')" class="size-3" /></button></TableHead>
            <TableHead class="text-right"><button class="inline-flex items-center gap-1" @click="emit('sort', 'margin_percent')">Маржа<component :is="sortIcon('margin_percent')" class="size-3" /></button></TableHead>
            <TableHead>Наличие</TableHead><TableHead class="text-right"><button class="inline-flex items-center gap-1" @click="emit('sort', 'quantity')">Кол-во<component :is="sortIcon('quantity')" class="size-3" /></button></TableHead><TableHead>Причина</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            <TableRow v-if="pending"><TableCell colspan="8" class="h-36 text-center text-muted-foreground">Загрузка истории…</TableCell></TableRow>
            <TableRow v-else-if="failed"><TableCell colspan="8" class="h-36 text-center"><p>Не удалось загрузить историю.</p><Button class="mt-2" variant="outline" @click="emit('retry')">Повторить</Button></TableCell></TableRow>
            <TableRow v-else-if="!items.length"><TableCell colspan="8" class="h-36 text-center text-muted-foreground">История по заданным фильтрам не найдена.</TableCell></TableRow>
            <TableRow v-for="state in items" :key="state.id">
              <TableCell class="whitespace-nowrap text-sm text-muted-foreground">{{ new Date(state.observed_at).toLocaleString('uk-UA') }}</TableCell>
              <TableCell class="text-right tabular-nums font-medium">{{ formatMoney(state.purchase_price, state.currency) }}</TableCell>
              <TableCell class="text-right tabular-nums">{{ formatMoney(state.rrp, state.currency) }}</TableCell>
              <TableCell class="text-right tabular-nums">{{ formatMoney(state.recommended_retail_income, state.currency) }}</TableCell>
              <TableCell class="text-right tabular-nums">{{ state.margin_percent === null ? '—' : `${Number(state.margin_percent).toFixed(1)}%` }}</TableCell>
              <TableCell><Badge :variant="state.availability === 'in_stock' ? 'secondary' : 'outline'">{{ availabilityLabel[state.availability] ?? state.availability }}</Badge></TableCell>
              <TableCell class="text-right tabular-nums">{{ state.quantity ?? '—' }}</TableCell>
              <TableCell class="whitespace-nowrap text-sm text-muted-foreground">{{ reasonLabel[state.change_reason] ?? state.change_reason }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      <footer class="flex shrink-0 items-center justify-between text-sm"><span class="text-muted-foreground">{{ total }} записей</span><div class="flex items-center gap-2"><Button variant="outline" size="icon" :disabled="filters.page <= 1" aria-label="Предыдущая страница" @click="emit('page', filters.page - 1)"><ChevronLeft /></Button><span>{{ filters.page }} / {{ totalPages }}</span><Button variant="outline" size="icon" :disabled="filters.page >= totalPages" aria-label="Следующая страница" @click="emit('page', filters.page + 1)"><ChevronRight /></Button></div></footer>
    </SheetContent>
  </Sheet>
</template>
