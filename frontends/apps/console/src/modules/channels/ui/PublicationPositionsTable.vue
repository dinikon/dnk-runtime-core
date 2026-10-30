<script setup lang="ts">
import { computed } from "vue";
import { useMediaQuery } from "@vueuse/core";
import { ExternalLink } from "@lucide/vue";
import {
  DataTable,
  type DataTableColumn,
} from "@/components/custom-ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PublicationCard } from "../model/publication.types";
import { publicationExternalUrl } from "../model/publication.thumbnail";
import PublicationThumbnail from "./PublicationThumbnail.vue";
const props = defineProps<{
  card: PublicationCard;
  requestedPublicationId: string;
}>();
const mobile = useMediaQuery("(max-width: 639px)");
type Column =
  | "title"
  | "sku"
  | "price"
  | "regularPrice"
  | "salePrice"
  | "stock"
  | "availability"
  | "status"
  | "received"
  | "actions";
const columns = computed<readonly DataTableColumn<Column>[]>(() => [
  {
    key: "title",
    label: "Позиция",
    width: mobile.value ? 180 : 260,
    pinned: "start",
  },
  { key: "sku", label: "Артикул / ID", width: 160 },
  { key: "price", label: "Цена", width: 180, align: "right" },
  { key: "stock", label: "Остаток", width: 180, align: "right" },
  { key: "availability", label: "Наличие", width: 150 },
  { key: "status", label: "Статус площадки", width: 160 },
  { key: "regularPrice", label: "Обычная цена", width: 180, align: "right" },
  { key: "salePrice", label: "Акционная цена", width: 180, align: "right" },
  { key: "received", label: "Получено", width: 180 },
  { key: "actions", label: "Действия", width: 68 },
]);
const labels: Record<string, string> = {
  in_stock: "В наличии",
  out_of_stock: "Нет в наличии",
  on_order: "Под заказ",
  removed: "Удалён из прайса",
};
const highlighted = computed(() =>
  props.requestedPublicationId !== props.card.id
    ? [props.requestedPublicationId]
    : [],
);
</script>
<template>
  <DataTable
    :rows="card.items"
    :columns="columns"
    :row-key="(item) => item.id"
    :selected-keys="highlighted"
    caption="Позиции публикации"
  >
    <template #cell="{ row: item, column }">
      <div
        v-if="column.key === 'title'"
        class="flex min-w-0 items-center gap-2"
        :aria-current="highlighted.includes(item.id) ? 'true' : undefined"
      >
        <PublicationThumbnail
          :src="publicationExternalUrl(item.mainImageUrl)"
          compact
        />
        <div class="min-w-0">
          <p
            class="truncate font-medium"
            :title="item.title ?? 'Перевод не получен'"
          >
            {{ item.title ?? "Перевод не получен" }}
          </p>
          <Badge
            v-if="
              card.rootKind === 'simple' &&
              card.items.length > 1 &&
              item.id === card.id
            "
            variant="outline"
            class="mt-1"
            >Основная позиция</Badge
          ><Badge
            v-if="highlighted.includes(item.id)"
            variant="outline"
            class="mt-1"
            >Позиция из ссылки</Badge
          >
          <p
            v-if="item.staleConfiguration"
            class="mt-1 text-xs text-muted-foreground"
          >
            Получено с предыдущими настройками
          </p>
        </div>
      </div>
      <div v-else-if="column.key === 'sku'" class="flex min-w-0 flex-col gap-1">
        <span class="truncate" :title="item.sku ?? undefined">{{
          item.sku ?? "Не получен"
        }}</span
        ><span
          class="truncate text-xs text-muted-foreground"
          :title="item.externalId"
          >{{ item.externalId }}</span
        >
      </div>
      <span
        v-else-if="
          column.key === 'price' ||
          column.key === 'regularPrice' ||
          column.key === 'salePrice'
        "
        class="block truncate tabular-nums"
        :title="
          item[column.key] === null
            ? 'Не получена'
            : item[column.key] + ' ' + item.currency
        "
        >{{
          item[column.key] === null
            ? "Не получена"
            : item[column.key] + " " + item.currency
        }}</span
      >
      <div
        v-else-if="column.key === 'stock'"
        class="flex min-w-0 flex-col gap-1"
      >
        <span
          class="truncate tabular-nums"
          :title="item.quantity ?? undefined"
          >{{ item.quantity ?? "Не получен" }}</span
        ><span
          v-if="item.stockMode === 'parent'"
          class="text-xs text-muted-foreground"
          >Общий остаток карточки</span
        >
      </div>
      <span v-else-if="column.key === 'availability'">{{
        labels[item.availability ?? ""] ?? "Не получено"
      }}</span>
      <span
        v-else-if="column.key === 'status'"
        class="block truncate"
        :title="item.status ?? undefined"
        >{{ item.status ?? "Не получен" }}</span
      >
      <span
        v-else-if="column.key === 'received'"
        class="text-muted-foreground"
        >{{ new Date(item.lastSeenAt).toLocaleString("ru-RU") }}</span
      >
      <template v-else-if="column.key === 'actions'"
        ><Button
          v-if="publicationExternalUrl(item.url)"
          as-child
          type="button"
          variant="ghost"
          size="icon-sm"
          class="min-h-11 min-w-11 sm:min-h-8 sm:min-w-8"
          ><a
            :href="publicationExternalUrl(item.url) ?? undefined"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Открыть на площадке"
            title="Открыть на площадке"
            ><ExternalLink /></a></Button
        ><span v-else class="text-xs text-muted-foreground"
          >Нет ссылки</span
        ></template
      >
    </template>
  </DataTable>
</template>
