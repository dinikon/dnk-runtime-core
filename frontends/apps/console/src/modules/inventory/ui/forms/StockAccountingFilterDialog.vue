<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  StockFilterKind,
  StockFilterOption,
  StockFilterOptionsPage,
} from "../../model/stock-accounting.types";
import { stockFilterNames } from "../../model/stock-accounting-navigation";
defineProps<{
  kind: StockFilterKind;
  search: string;
  page: StockFilterOptionsPage;
  offset: number;
  loading: boolean;
  error: string;
}>();
const emit = defineEmits<{
  close: [];
  search: [value: string];
  select: [value: StockFilterOption];
  page: [offset: number];
  retry: [];
}>();
</script>
<template>
  <Dialog :open="true" @update:open="!$event && emit('close')"
    ><DialogContent class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      ><DialogHeader
        ><DialogTitle>Фильтр: {{ stockFilterNames[kind] }}</DialogTitle
        ><DialogDescription
          >Поиск по справочнику. Неактивные объекты также доступны для просмотра
          истории.</DialogDescription
        ></DialogHeader
      ><Input
        :model-value="search"
        type="search"
        aria-label="Поиск значения фильтра"
        @update:model-value="emit('search', String($event))"
      />
      <p v-if="loading" role="status">Поиск…</p>
      <p v-if="error" role="alert">
        {{ error }} <Button @click="emit('retry')">Повторить поиск</Button>
      </p>
      <div v-if="!loading" class="max-h-80 overflow-y-auto rounded-md border">
        <p v-if="!page.items.length" class="p-3 text-sm text-muted-foreground">
          Ничего не найдено.
        </p>
        <button
          v-for="item in page.items"
          :key="item.id"
          type="button"
          class="block w-full break-words border-b p-3 text-left text-sm hover:bg-muted"
          @click="emit('select', item)"
        >
          {{ item.label }}
        </button>
      </div>
      <div class="flex items-center justify-between">
        <Button
          variant="outline"
          :disabled="loading || offset === 0"
          @click="emit('page', Math.max(0, offset - 20))"
          >Назад</Button
        ><span class="text-xs">{{ page.total }} найдено</span
        ><Button
          variant="outline"
          :disabled="loading || offset + 20 >= page.total"
          @click="emit('page', offset + 20)"
          >Далее</Button
        >
      </div></DialogContent
    ></Dialog
  >
</template>
