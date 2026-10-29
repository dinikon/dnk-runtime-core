<script setup lang="ts">
import {
  Ellipsis,
  Package,
  Pencil,
  SquareArrowOutUpRight,
  Trash2,
} from "@lucide/vue";
import { DataTable } from "@/components/custom-ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { CatalogListItem } from "../../model/catalog.types";
import { statusLabels, stockLabels } from "../../model/product-labels";
import { catalogListPrice } from "../../model/catalog-list.presentation";
import { catalogItemsColumns } from "./catalog-items.columns";

defineProps<{
  items: readonly CatalogListItem[];
  disabled: boolean;
  imageUrl: (item: CatalogListItem) => string | undefined;
}>();
const emit = defineEmits<{
  open: [id: string];
  edit: [id: string];
  remove: [item: CatalogListItem];
}>();
</script>

<template>
  <DataTable
    :rows="items"
    :columns="catalogItemsColumns"
    :row-key="(item) => item.id"
    caption="Товары"
    @row-activate="emit('open', $event.id)"
  >
    <template #header="{ column }">
      <span :class="column.key === 'actions' ? 'sr-only' : undefined">{{
        column.label
      }}</span>
    </template>
    <template #cell="{ row: item, column }">
      <Button
        v-if="column.key === 'title'"
        type="button"
        variant="ghost"
        size="sm"
        class="h-auto max-w-full justify-start p-0"
        :aria-label="`Открыть ${item.title ?? 'товар без перевода'}`"
        @click="emit('open', item.id)"
      >
        <span
          class="flex size-6 shrink-0 items-center justify-center overflow-hidden rounded bg-muted"
        >
          <img
            v-if="item.primaryImage"
            :src="imageUrl(item)"
            alt=""
            class="size-full object-cover"
            loading="lazy"
          />
          <Package v-else aria-hidden="true" />
        </span>
        <span class="truncate" :title="item.title ?? 'Без перевода'">{{
          item.title ?? "Без перевода"
        }}</span>
      </Button>
      <span
        v-else-if="column.key === 'sku'"
        class="block truncate"
        :title="item.sku ?? undefined"
        >{{ item.sku ?? "—" }}</span
      >
      <span
        v-else-if="column.key === 'kind'"
        class="inline-flex items-center gap-2"
      >
        {{
          item.kind === "variable"
            ? "С вариантами"
            : item.kind === "variant"
              ? "Вариант"
              : "Товар"
        }}
        <Badge
          v-if="item.kind === 'variable'"
          variant="outline"
          :aria-label="`Вариантов: ${item.variant_count ?? 0}`"
          >{{ item.variant_count ?? 0 }}</Badge
        >
      </span>
      <Badge
        v-else-if="column.key === 'status'"
        :variant="item.status === 'active' ? 'secondary' : 'outline'"
        >{{ statusLabels[item.status] }}</Badge
      >
      <span
        v-else-if="column.key === 'price'"
        class="block truncate tabular-nums"
        :title="catalogListPrice(item)"
        >{{ catalogListPrice(item) }}</span
      >
      <span v-else-if="column.key === 'stock'">{{
        stockLabels[item.stockStatus ?? ""] ?? "Не задано"
      }}</span>
      <DropdownMenu v-else-if="column.key === 'actions'">
        <DropdownMenuTrigger as-child
          ><Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled"
            :aria-label="`Действия: ${item.title ?? item.sku ?? item.id}`"
            ><Ellipsis /></Button
        ></DropdownMenuTrigger>
        <DropdownMenuContent align="end" class="w-48">
          <DropdownMenuGroup>
            <DropdownMenuItem @select="emit('open', item.id)"
              ><SquareArrowOutUpRight />Открыть</DropdownMenuItem
            >
            <DropdownMenuItem @select="emit('edit', item.id)"
              ><Pencil />Редактировать</DropdownMenuItem
            >
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup
            ><DropdownMenuItem
              variant="destructive"
              @select="emit('remove', item)"
              ><Trash2 />Удалить</DropdownMenuItem
            ></DropdownMenuGroup
          >
        </DropdownMenuContent>
      </DropdownMenu>
    </template>
  </DataTable>
</template>
