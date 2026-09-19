<script setup lang="ts">
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { PartnerOffer, PartnerOfferState } from "../../model/types";
import { formatMoney } from "../../model/query-state";

defineProps<{
  offer: PartnerOffer | null;
  items: PartnerOfferState[];
  pending: boolean;
}>();
defineEmits<{ close: [] }>();
</script>

<template>
  <Sheet :open="offer !== null" @update:open="(open) => { if (!open) $emit('close') }">
    <SheetContent class="w-full overflow-y-auto sm:max-w-xl"><SheetHeader><SheetTitle>{{ offer?.title }}</SheetTitle><SheetDescription>{{ offer?.sku }} · история закупочной цены и остатка</SheetDescription></SheetHeader>
      <div class="mt-6 grid gap-3"><div v-if="pending" class="text-sm text-muted-foreground">Загрузка истории…</div><div v-for="state in items" :key="state.id" class="rounded-lg border p-3"><div class="flex justify-between"><strong>{{ formatMoney(state.purchase_price, state.currency) }}</strong><span class="text-xs text-muted-foreground">{{ new Date(state.observed_at).toLocaleString('uk-UA') }}</span></div><div class="mt-1 text-sm text-muted-foreground">РРЦ: {{ formatMoney(state.rrp, state.currency) }} · РРД: {{ formatMoney(state.recommended_retail_income, state.currency) }} · Маржа: {{ state.margin_percent === null ? '—' : `${Number(state.margin_percent).toFixed(1)}%` }}</div><div class="mt-1 text-xs text-muted-foreground">{{ state.availability }} · {{ state.quantity ?? 'без количества' }} · {{ state.change_reason }}</div></div></div>
    </SheetContent>
  </Sheet>
</template>
