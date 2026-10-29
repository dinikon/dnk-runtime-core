<script setup lang="ts">
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ProductStatus } from "../../model/product.types";
import type { LocaleOption } from "../../model/catalog.types";
import CatalogSearchBar from "../CatalogSearchBar.vue";

defineProps<{
  search: string;
  status: ProductStatus | undefined;
  locale: string;
  locales: readonly LocaleOption[];
}>();
const emit = defineEmits<{
  search: [value: string];
  status: [value: ProductStatus | undefined];
  locale: [value: string];
}>();
</script>

<template>
  <div class="flex shrink-0 flex-wrap items-center justify-between gap-3">
    <CatalogSearchBar :value="search" @search="emit('search', $event)" />
    <div class="flex flex-wrap items-center gap-2">
      <Select
        :model-value="status ?? 'all'"
        @update:model-value="
          emit(
            'status',
            $event === 'all' ? undefined : ($event as ProductStatus),
          )
        "
      >
        <SelectTrigger class="w-40" aria-label="Статус товаров"
          ><SelectValue
        /></SelectTrigger>
        <SelectContent
          ><SelectGroup>
            <SelectItem value="all">Все статусы</SelectItem
            ><SelectItem value="draft">Черновики</SelectItem
            ><SelectItem value="active">Активные</SelectItem
            ><SelectItem value="archived">В архиве</SelectItem>
          </SelectGroup></SelectContent
        >
      </Select>
      <Select
        :model-value="locale || undefined"
        @update:model-value="emit('locale', String($event))"
      >
        <SelectTrigger class="w-40" aria-label="Язык каталога"
          ><SelectValue v-if="locale"
            >{{
              locales.find((option) => option.code === locale)?.name ?? locale
            }}
            · {{ locale }}</SelectValue
          ><SelectValue v-else placeholder="Выберите язык"
        /></SelectTrigger>
        <SelectContent
          ><SelectGroup
            ><SelectItem
              v-for="option in locales"
              :key="option.code"
              :value="option.code"
              >{{ option.name }} · {{ option.code }}</SelectItem
            ></SelectGroup
          ></SelectContent
        >
      </Select>
    </div>
  </div>
</template>
