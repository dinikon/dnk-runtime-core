<script setup lang="ts">
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { PublicationCard } from "../model/publication.types";
import { bindingStates } from "../model/bindings/binding.types";
import { publicationThumbnail } from "../model/publication.thumbnail";
import PublicationThumbnail from "./PublicationThumbnail.vue";

defineProps<{ items: PublicationCard[] }>();
const emit = defineEmits<{ open: [id: string] }>();
function itemLabel(card: PublicationCard): string {
  if (card.rootKind === "variable")
    return card.rootSku?.trim() || card.rootExternalId;
  const selected =
    card.items.find((item) => item.id === card.selectedPublicationId) ??
    card.items[0];
  return selected?.sku ?? selected?.externalId ?? "Карточка с вариациями";
}
</script>

<template>
  <Table class="min-w-[720px]" tabindex="0" aria-label="Таблица публикаций">
    <TableHeader class="sticky top-0 z-10 bg-background">
      <TableRow>
        <TableHead class="w-full px-3">Товар</TableHead>
        <TableHead class="px-3 text-right">Позиции</TableHead>
        <TableHead class="px-3 text-right">Цена</TableHead>
        <TableHead class="px-3">Получено</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      <TableRow v-for="card in items" :key="card.id">
        <TableCell class="px-3 py-2">
          <div class="flex min-w-64 items-center gap-3">
            <PublicationThumbnail :src="publicationThumbnail(card)" />
            <div class="flex min-w-0 flex-col gap-1">
              <button
                type="button"
                class="line-clamp-2 text-left font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                @click="emit('open', card.id)"
              >
                {{ card.title ?? "Перевод не получен" }}
              </button>
              <p class="text-xs text-muted-foreground">{{ itemLabel(card) }}</p>
              <span
                class="text-xs"
                :class="
                  card.bindings?.some((v) => v.state === 'conflict')
                    ? 'text-destructive'
                    : 'text-muted-foreground'
                "
                >{{
                  card.bindings?.length
                    ? card.bindings
                        .map((v) => bindingStates[v.state] ?? v.state)
                        .join(" · ")
                    : "Без привязки к Catalog"
                }}</span
              >
              <Badge
                v-if="card.items.some((item) => item.staleConfiguration)"
                variant="outline"
                class="self-start"
                >Предыдущие настройки</Badge
              >
            </div>
          </div>
        </TableCell>
        <TableCell class="px-3 text-right tabular-nums">{{
          card.items.length
        }}</TableCell>
        <TableCell class="whitespace-nowrap px-3 text-right tabular-nums">{{
          card.minPrice === null
            ? "Не получена"
            : card.minPrice +
              (card.maxPrice !== card.minPrice ? "–" + card.maxPrice : "") +
              " " +
              (card.currency ?? "")
        }}</TableCell>
        <TableCell class="whitespace-nowrap px-3 text-muted-foreground">{{
          new Date(card.lastSeenAt).toLocaleString("ru-RU")
        }}</TableCell>
      </TableRow>
    </TableBody>
  </Table>
</template>
