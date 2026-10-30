<script setup lang="ts">
import { computed } from "vue";
import { useMediaQuery } from "@vueuse/core";
import {
  Ellipsis,
  Package,
  Pencil,
  Trash2,
  ChevronRight,
  ChevronDown,
} from "@lucide/vue";
import {
  DataTable,
  type DataTableColumn,
} from "@/components/custom-ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { CatalogListItem } from "../../model/catalog.types";
import type {
  CatalogVariantExpansions,
  ExpandedCatalogVariants,
  CatalogQuickEditSection,
} from "../../model/catalog-table.types";
import { statusLabels, stockLabels } from "../../model/product-labels";
import {
  catalogListPrice,
  catalogListStock,
} from "../../model/catalog-list.presentation";
import {
  catalogItemsColumns,
  type CatalogItemsColumn,
} from "./catalog-items.columns";

const props = withDefaults(
  defineProps<{
    items: readonly CatalogListItem[];
    disabled: boolean;
    imageUrl: (item: CatalogListItem) => string | undefined;
    columns?: readonly DataTableColumn<CatalogItemsColumn>[];
    caption?: string;
    expanded?: CatalogVariantExpansions;
    canQuickEdit?: boolean;
  }>(),
  { columns: () => catalogItemsColumns, caption: "Товары", canQuickEdit: true },
);
const emit = defineEmits<{
  open: [id: string];
  remove: [item: CatalogListItem];
  openVariant: [rootId: string, id: string];
  toggle: [id: string];
  variantPage: [id: string, offset: number];
  variantRetry: [id: string];
  quickEdit: [item: CatalogListItem, section: CatalogQuickEditSection];
}>();
interface CatalogTableRow {
  id: string;
  item: CatalogListItem;
  parentId?: string;
  detail?: ExpandedCatalogVariants;
}
const rows = computed<CatalogTableRow[]>(() =>
  props.items.flatMap((item) => {
    const expansion = props.expanded?.[item.id];
    return [
      { id: item.id, item },
      ...(expansion
        ? [
            ...expansion.items.map((variant) => ({
              id: variant.id,
              item: variant,
              parentId: item.id,
            })),
            { id: `${item.id}:variants`, item, detail: expansion },
          ]
        : []),
    ];
  }),
);
const mobile = useMediaQuery("(max-width: 639px)");
const columns = computed(() =>
  props.columns.map((column) =>
    mobile.value && column.key === "title" ? { ...column, width: 190 } : column,
  ),
);
function open(row: CatalogTableRow): void {
  if (props.disabled || row.detail) return;
  if (row.parentId) emit("openVariant", row.parentId, row.item.id);
  else emit("open", row.item.id);
}
</script>
<template>
  <DataTable
    :rows="rows"
    :columns="columns"
    :row-key="(row) => row.id"
    :is-detail-row="(row) => !!row.detail"
    :caption="caption"
    @row-activate="open"
  >
    <template #header="{ column }"
      ><span :class="column.key === 'actions' ? 'sr-only' : undefined">{{
        column.label
      }}</span></template
    >
    <template #cell="{ row, column }">
      <div
        v-if="column.key === 'title'"
        :class="['flex min-w-0 items-center gap-1', row.parentId && 'pl-8']"
      >
        <Button
          v-if="row.item.kind === 'variable' && expanded !== undefined"
          type="button"
          variant="ghost"
          size="icon-sm"
          class="min-h-11 min-w-11 shrink-0 sm:min-h-8 sm:min-w-8"
          :disabled="disabled"
          :aria-label="`${expanded[row.item.id] ? 'Свернуть' : 'Показать'} варианты: ${row.item.title ?? 'Без перевода'}`"
          :aria-expanded="!!expanded[row.item.id]"
          @click.stop="emit('toggle', row.item.id)"
          @dblclick.stop
          ><ChevronDown v-if="expanded[row.item.id]" /><ChevronRight v-else
        /></Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="h-auto min-h-11 min-w-0 flex-1 justify-start p-0 sm:min-h-8"
          :disabled="disabled"
          :aria-label="`Открыть ${row.item.title ?? 'товар без перевода'}`"
          @click="open(row)"
        >
          <span
            class="flex size-6 shrink-0 items-center justify-center overflow-hidden rounded bg-muted"
            ><img
              v-if="row.item.primaryImage"
              :src="imageUrl(row.item)"
              alt=""
              class="size-full object-cover"
              loading="lazy" /><Package v-else aria-hidden="true"
          /></span>
          <span class="truncate" :title="row.item.title ?? 'Без перевода'">{{
            row.item.title ?? "Без перевода"
          }}</span>
        </Button>
      </div>
      <span
        v-else-if="column.key === 'sku'"
        class="block truncate"
        :title="row.item.sku ?? undefined"
        >{{ row.item.sku ?? "—" }}</span
      >
      <span
        v-else-if="column.key === 'kind'"
        class="inline-flex items-center gap-2"
        >{{
          row.item.kind === "variable"
            ? "С вариантами"
            : row.item.kind === "variant"
              ? "Вариант"
              : "Товар"
        }}<Badge
          v-if="row.item.kind === 'variable'"
          variant="outline"
          :aria-label="`Вариантов: ${row.item.variant_count ?? 0}`"
          >{{ row.item.variant_count ?? 0 }}</Badge
        ></span
      >
      <Badge
        v-else-if="column.key === 'status'"
        :variant="row.item.status === 'active' ? 'secondary' : 'outline'"
        >{{ statusLabels[row.item.status] }}</Badge
      >
      <template v-else-if="column.key === 'price'">
        <span
          v-if="row.item.kind === 'variable'"
          class="block truncate tabular-nums"
          :title="`${catalogListPrice(row.item)}. Цена изменяется в вариантах.`"
          >{{ catalogListPrice(row.item) }}</span
        >
        <Button
          v-else
          type="button"
          variant="ghost"
          size="sm"
          class="h-auto min-h-11 w-full min-w-0 justify-end px-0 sm:min-h-8"
          :disabled="disabled || !canQuickEdit"
          :aria-label="`Изменить цену: ${row.item.title ?? row.item.sku ?? row.item.id}`"
          :title="catalogListPrice(row.item)"
          @click.stop="emit('quickEdit', row.item, 'price')"
          @dblclick.stop
          ><span class="truncate tabular-nums">{{
            catalogListPrice(row.item)
          }}</span
          ><Pencil data-icon="inline-end"
        /></Button>
      </template>
      <Button
        v-else-if="column.key === 'stock'"
        type="button"
        variant="ghost"
        size="sm"
        class="h-auto min-h-11 w-full min-w-0 justify-end px-0 sm:min-h-8"
        :disabled="disabled || !canQuickEdit"
        :aria-label="`Изменить остаток: ${row.item.title ?? row.item.sku ?? row.item.id}`"
        @click.stop="emit('quickEdit', row.item, 'stock')"
        @dblclick.stop
      >
        <span class="flex min-w-0 flex-col items-end gap-0.5"
          ><span class="truncate tabular-nums">{{
            catalogListStock(row.item)
          }}</span
          ><span
            v-if="row.item.kind !== 'variable'"
            class="text-xs text-muted-foreground"
            >{{ stockLabels[row.item.stockStatus ?? ""] ?? "Не задано" }}</span
          ></span
        ><Pencil data-icon="inline-end" />
      </Button>
      <DropdownMenu v-else-if="column.key === 'actions'">
        <DropdownMenuTrigger as-child
          ><Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled"
            :aria-label="`Действия: ${row.item.title ?? row.item.sku ?? row.item.id}`"
            ><Ellipsis /></Button
        ></DropdownMenuTrigger>
        <DropdownMenuContent align="end" class="w-48"
          ><DropdownMenuGroup
            ><DropdownMenuItem @select="open(row)"
              ><Pencil />Редактировать</DropdownMenuItem
            ></DropdownMenuGroup
          ><template v-if="!row.parentId"
            ><DropdownMenuSeparator /><DropdownMenuGroup
              ><DropdownMenuItem
                variant="destructive"
                @select="emit('remove', row.item)"
                ><Trash2 />Удалить</DropdownMenuItem
              ></DropdownMenuGroup
            ></template
          ></DropdownMenuContent
        >
      </DropdownMenu>
    </template>
    <template #detail="{ row }">
      <div
        v-if="row.detail"
        class="sticky left-3 flex w-fit max-w-[calc(100vw-4rem)] flex-col items-start gap-2"
        :aria-label="`Варианты: ${row.item.title ?? row.item.id}`"
      >
        <Alert v-if="row.detail.error" variant="destructive"
          ><AlertDescription class="flex items-center gap-2"
            >{{ row.detail.error
            }}<Button
              type="button"
              variant="outline"
              :disabled="row.detail.fetching"
              @click="emit('variantRetry', row.item.id)"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        >
        <p
          v-if="row.detail.fetching"
          role="status"
          class="flex items-center gap-2 text-sm text-muted-foreground"
        >
          <Spinner />{{
            row.detail.loading ? "Загрузка вариантов…" : "Обновление вариантов…"
          }}
        </p>
        <p
          v-if="
            !row.detail.loading && !row.detail.error && !row.detail.items.length
          "
          class="text-sm text-muted-foreground"
        >
          {{
            row.detail.offset
              ? "На этой странице нет вариантов"
              : "Вариантов пока нет"
          }}
        </p>
        <div
          v-if="!row.detail.loading && !row.detail.error"
          class="flex items-center gap-3 text-sm"
        >
          <span
            >Варианты: {{ row.detail.total ? row.detail.offset + 1 : 0 }}–{{
              row.detail.offset + row.detail.items.length
            }}
            из {{ row.detail.total }}</span
          >
          <Button
            v-if="row.detail.offset"
            type="button"
            variant="outline"
            size="sm"
            :disabled="row.detail.fetching"
            aria-label="Предыдущие варианты"
            @click="
              emit(
                'variantPage',
                row.item.id,
                row.detail.offset - row.detail.limit,
              )
            "
            >Назад</Button
          >
          <Button
            v-if="row.detail.offset + row.detail.limit < row.detail.total"
            type="button"
            variant="outline"
            size="sm"
            :disabled="row.detail.fetching"
            aria-label="Следующие варианты"
            @click="
              emit(
                'variantPage',
                row.item.id,
                row.detail.offset + row.detail.limit,
              )
            "
            >Далее</Button
          >
          <Button
            v-if="row.detail.offset && !row.detail.items.length"
            type="button"
            variant="outline"
            size="sm"
            @click="emit('variantPage', row.item.id, 0)"
            >К первым вариантам</Button
          >
        </div>
      </div>
    </template>
  </DataTable>
</template>
