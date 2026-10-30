<script setup lang="ts">
import { DataTable } from "@/components/custom-ui/data-table";
import { computed } from "vue";
import { useMediaQuery } from "@vueuse/core";
import { publicationsColumns } from "./publications.columns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Link2 } from "@lucide/vue";
import type { PublicationCard } from "../model/publication.types";
import { bindingStates } from "../model/bindings/binding.types";
import { publicationThumbnail } from "../model/publication.thumbnail";
import PublicationThumbnail from "./PublicationThumbnail.vue";
import PublicationActions from "./PublicationActions.vue";
import {
  publicationPrice,
  publicationStock,
} from "../model/publication-summary";

defineProps<{
  items: PublicationCard[];
  busy?: boolean;
}>();
const emit = defineEmits<{
  open: [id: string];
  unlink: [publicationId: string, bindingId: string];
  openCatalog: [id: string];
  connect: [id: string];
  create: [id: string];
}>();
const mobile = useMediaQuery("(max-width: 639px)");
const columns = computed(() =>
  publicationsColumns.map((column) =>
    mobile.value && column.key === "publication"
      ? { ...column, width: 180 }
      : mobile.value && column.key === "actions"
        ? { ...column, pinned: undefined }
        : column,
  ),
);
function itemLabel(card: PublicationCard): string {
  if (card.rootKind === "variable")
    return card.rootSku?.trim() || card.rootExternalId;
  const selected =
    card.items.find((item) => item.id === card.selectedPublicationId) ??
    card.items[0];
  return selected?.sku ?? selected?.externalId ?? "Карточка с вариациями";
}
function catalogTargets(
  card: PublicationCard,
): { id: string; label: string }[] {
  return [
    ...new Map(
      card.bindings.map((binding) => [
        binding.catalogRootId,
        {
          id: binding.catalogRootId,
          label: binding.catalogTitle ?? "Товар без названия",
        },
      ]),
    ).values(),
  ];
}
</script>

<template>
  <DataTable
    :rows="items"
    :columns="columns"
    :row-key="(row) => row.id"
    caption="Публикации"
    class="max-h-[65dvh] lg:max-h-none"
    @row-activate="!busy && emit('open', $event.id)"
  >
    <template #cell="{ row: card, column }">
      <div
        v-if="column.key === 'publication'"
        class="flex min-w-0 items-center gap-2"
      >
        <PublicationThumbnail :src="publicationThumbnail(card)" compact />
        <div class="min-w-0">
          <button
            type="button"
            class="block w-full truncate text-left font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :disabled="busy"
            :title="card.title ?? 'Перевод не получен'"
            @click="emit('open', card.id)"
          >
            {{ card.title ?? "Перевод не получен" }}</button
          ><Badge
            v-if="card.items.some((item) => item.staleConfiguration)"
            variant="outline"
            class="mt-1"
            >Предыдущие настройки</Badge
          >
        </div>
      </div>
      <span
        v-else-if="column.key === 'sku'"
        class="block truncate"
        :title="itemLabel(card)"
        >{{ itemLabel(card) }}</span
      >
      <span v-else-if="column.key === 'positions'" class="tabular-nums">{{
        card.items.length
      }}</span>
      <span
        v-else-if="column.key === 'price'"
        class="block truncate tabular-nums"
        :title="publicationPrice(card)"
        >{{ publicationPrice(card) }}</span
      >
      <span
        v-else-if="column.key === 'stock'"
        class="block truncate tabular-nums"
        :title="publicationStock(card)"
        >{{ publicationStock(card) }}</span
      >
      <div v-else-if="column.key === 'binding'" class="flex flex-wrap gap-1">
        <Badge
          v-for="binding in card.bindings"
          :key="binding.id"
          :variant="binding.state === 'conflict' ? 'destructive' : 'secondary'"
          :title="binding.catalogTitle ?? undefined"
          >{{ bindingStates[binding.state] ?? binding.state }}</Badge
        ><Button
          v-if="!card.bindings.length"
          type="button"
          variant="ghost"
          size="sm"
          class="min-h-11 px-0 sm:min-h-8"
          :disabled="busy"
          @click.stop="emit('connect', card.id)"
          @dblclick.stop
          ><Link2 data-icon="inline-start" />Создать связь</Button
        >
      </div>
      <span
        v-else-if="column.key === 'received'"
        class="whitespace-nowrap text-muted-foreground"
        >{{ new Date(card.lastSeenAt).toLocaleString("ru-RU") }}</span
      >
      <PublicationActions
        v-else-if="column.key === 'actions'"
        :busy="busy"
        can-connect
        :catalog-targets="catalogTargets(card)"
        :unlink-targets="
          card.bindings.map((binding) => ({
            id: binding.id,
            label: binding.catalogTitle ?? 'Товар без названия',
          }))
        "
        @publication="emit('open', card.id)"
        @catalog="emit('openCatalog', $event)"
        @unlink="emit('unlink', card.id, $event)"
        @connect="emit('connect', card.id)"
        @create="emit('create', card.id)"
      />
    </template>
  </DataTable>
</template>
