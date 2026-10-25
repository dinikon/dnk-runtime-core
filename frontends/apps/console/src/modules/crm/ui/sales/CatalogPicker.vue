<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { CatalogChoice } from "../../model/sales.types";
import SalesFeedback from "./SalesFeedback.vue";
defineProps<{
  open: boolean;
  search: string;
  items: CatalogChoice[];
  loading: boolean;
  error: string;
  pending?: boolean;
}>();
defineEmits<{
  "update:open": [value: boolean];
  "update:search": [value: string];
  select: [id: string];
  retry: [];
}>();
</script>
<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)"
    ><DialogContent class="max-h-[85dvh] overflow-auto"
      ><DialogHeader
        ><DialogTitle>Добавить из каталога</DialogTitle
        ><DialogDescription
          >Добавляется независимый коммерческий снимок. Текущие цены каталога не
          меняют сохранённую продажу.</DialogDescription
        ></DialogHeader
      ><Input
        :model-value="search"
        aria-label="Поиск товара в каталоге"
        placeholder="Название или артикул"
        @update:model-value="$emit('update:search', String($event))"
      /><SalesFeedback
        :loading="loading"
        :error="error"
        :empty="!items.length"
        @retry="$emit('retry')"
        ><div class="flex flex-col gap-2">
          <Button
            v-for="item in items"
            :key="item.id"
            variant="outline"
            class="h-auto justify-between whitespace-normal py-3 text-left"
            :disabled="pending"
            @click="$emit('select', item.id)"
            ><span>{{ item.title || item.sku || "Позиция каталога" }}</span
            ><span
              >{{ item.price ?? "Цена не задана" }} {{ item.currency }}</span
            ></Button
          >
        </div></SalesFeedback
      ></DialogContent
    ></Dialog
  >
</template>
