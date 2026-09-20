<script setup lang="ts">
import OfferMoneyValue from "@/modules/currency/ui/OfferMoneyValue.vue";
import { ArrowDown, ArrowUp } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { OfferFilters, PartnerOffer } from "../../model/types";
import { formatMoney } from "../../model/query-state";

const props = defineProps<{
  items: PartnerOffer[];
  filters: OfferFilters;
  pending: boolean;
  failed: boolean;
  filtered: boolean;
}>();
const emit = defineEmits<{
  sort: [field: string];
  retry: [];
  select: [offer: PartnerOffer];
}>();
const sortIcon = (field: string) =>
  props.filters.sort === field && props.filters.direction === "asc"
    ? ArrowUp
    : ArrowDown;
</script>

<template>
  <section class="min-h-0 flex-1 overflow-auto rounded-lg border bg-background">
    <Table>
      <TableHeader class="sticky top-0 z-10 bg-background"
        ><TableRow>
          <TableHead class="sticky left-0 z-20 min-w-40 bg-background pl-4"
            ><button
              class="inline-flex items-center gap-1"
              @click="emit('sort', 'sku')"
            >
              SKU / внешний ID<component
                :is="sortIcon('sku')"
                class="size-3"
              /></button
          ></TableHead>
          <TableHead
            ><button
              class="inline-flex items-center gap-1"
              @click="emit('sort', 'title')"
            >
              Название<component
                :is="sortIcon('title')"
                class="size-3"
              /></button
          ></TableHead>
          <TableHead>Прайс-лист</TableHead>
          <TableHead class="text-right"
            ><button
              class="inline-flex items-center gap-1"
              @click="emit('sort', 'purchase_price')"
            >
              Закупочная цена<component
                :is="sortIcon('purchase_price')"
                class="size-3"
              /></button
          ></TableHead>
          <TableHead class="text-right"
            ><button
              class="inline-flex items-center gap-1"
              @click="emit('sort', 'rrp')"
            >
              РРЦ<component :is="sortIcon('rrp')" class="size-3" /></button
          ></TableHead>
          <TableHead class="text-right"
            ><button
              class="inline-flex items-center gap-1"
              @click="emit('sort', 'recommended_retail_income')"
            >
              РРД<component
                :is="sortIcon('recommended_retail_income')"
                class="size-3"
              /></button
          ></TableHead>
          <TableHead class="text-right"
            ><button
              class="inline-flex items-center gap-1"
              @click="emit('sort', 'margin_percent')"
            >
              Маржа<component
                :is="sortIcon('margin_percent')"
                class="size-3"
              /></button
          ></TableHead>
          <TableHead>Наличие</TableHead
          ><TableHead class="text-right">Изменений</TableHead
          ><TableHead>Обновлено</TableHead>
        </TableRow></TableHeader
      >
      <TableBody>
        <TableRow v-if="pending"
          ><TableCell
            colspan="10"
            class="h-40 text-center text-muted-foreground"
            >Загрузка офферов…</TableCell
          ></TableRow
        >
        <TableRow v-else-if="failed"
          ><TableCell colspan="10" class="h-40 text-center"
            ><p>Не удалось загрузить офферы.</p>
            <Button class="mt-2" variant="outline" @click="emit('retry')"
              >Повторить</Button
            ></TableCell
          ></TableRow
        >
        <TableRow v-else-if="!items.length"
          ><TableCell
            colspan="10"
            class="h-40 text-center text-muted-foreground"
            >{{
              filtered
                ? "Ничего не найдено — измените фильтры."
                : "Офферы появятся после первой синхронизации."
            }}</TableCell
          ></TableRow
        >
        <TableRow
          v-for="offer in items"
          :key="offer.id"
          class="cursor-pointer"
          tabindex="0"
          @click="emit('select', offer)"
          @keydown.enter="emit('select', offer)"
        >
          <TableCell class="sticky left-0 z-10 min-w-40 bg-background pl-4"
            ><div class="font-medium">{{ offer.sku }}</div>
            <div class="text-xs text-muted-foreground">
              {{ offer.external_id }}
            </div></TableCell
          >
          <TableCell class="max-w-80"
            ><div class="truncate font-medium" :title="offer.title">
              {{ offer.title }}
            </div></TableCell
          >
          <TableCell>{{ offer.price_list_title }}</TableCell>
          <TableCell class="text-right tabular-nums"
            >{{ formatMoney(offer.purchase_price, offer.currency ?? "UAH")
            }}<OfferMoneyValue
              :value="offer.current_conversion"
              :label="
                filters.businessDate ? 'На выбранную дату ≈' : 'Сейчас ≈'
              " /><OfferMoneyValue
              :value="offer.historical_conversion"
              label="При импорте"
          /></TableCell>
          <TableCell class="text-right tabular-nums"
            >{{ formatMoney(offer.rrp, offer.currency ?? "UAH")
            }}<OfferMoneyValue
              :value="offer.current_conversion"
              kind="rrp"
              :label="
                filters.businessDate ? 'На выбранную дату ≈' : 'Сейчас ≈'
              " /><OfferMoneyValue
              :value="offer.historical_conversion"
              kind="rrp"
              label="При импорте"
          /></TableCell>
          <TableCell
            class="text-right tabular-nums"
            :class="
              Number(offer.recommended_retail_income) < 0
                ? 'text-destructive'
                : ''
            "
            >{{
              formatMoney(
                offer.recommended_retail_income,
                offer.currency ?? "UAH",
              )
            }}</TableCell
          >
          <TableCell class="text-right tabular-nums">{{
            offer.margin_percent === null
              ? "—"
              : `${Number(offer.margin_percent).toFixed(1)}%`
          }}</TableCell>
          <TableCell
            ><Badge
              :variant="
                offer.availability === 'in_stock' ? 'secondary' : 'outline'
              "
              >{{
                offer.availability === "in_stock"
                  ? "В наличии"
                  : offer.availability === "out_of_stock"
                    ? "Нет в наличии"
                    : "Неизвестно"
              }}<span v-if="offer.quantity !== null">
                · {{ offer.quantity }}</span
              ></Badge
            ></TableCell
          >
          <TableCell class="text-right tabular-nums">{{
            offer.change_count
          }}</TableCell>
          <TableCell class="whitespace-nowrap text-sm text-muted-foreground">{{
            offer.observed_at
              ? new Date(offer.observed_at).toLocaleString("uk-UA")
              : "—"
          }}</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </section>
</template>
