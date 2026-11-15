<script setup lang="ts">
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { ReturnSource } from "../../model/return-posting.types";
defineProps<{
  search: string;
  items: readonly ReturnSource[];
  loading: boolean;
  error: string;
  offset: number;
  total: number;
}>();
const emit = defineEmits<{
  close: [];
  search: [value: string];
  select: [value: ReturnSource];
  page: [offset: number];
  retry: [];
}>();
</script>
<template>
  <Dialog :open="true" @update:open="!$event && emit('close')"
    ><DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-xl"
      ><DialogHeader
        ><DialogTitle>Выбор исходной позиции</DialogTitle
        ><DialogDescription
          >Физический запас выбранного SKU в складе и у владельца документа.
          Позицию выберите вручную.</DialogDescription
        ></DialogHeader
      >
      <label class="text-sm"
        >Поиск по локации, партии или серии<Input
          :model-value="search"
          @update:model-value="emit('search', String($event))"
      /></label>
      <p v-if="loading" role="status">Загрузка позиций…</p>
      <p v-if="error" role="alert" class="text-sm text-destructive">
        {{ error
        }}<Button variant="outline" :disabled="loading" @click="emit('retry')"
          >Повторить</Button
        >
      </p>
      <p
        v-if="!loading && !error && !items.length"
        class="text-sm text-muted-foreground"
      >
        Положительный физический запас не найден.
      </p>
      <div class="flex flex-col gap-2">
        <Button
          v-for="item in items"
          :key="item.id"
          variant="outline"
          class="h-auto justify-start whitespace-normal text-left"
          :disabled="
            loading ||
            !!error ||
            !/[1-9]/.test(item.onHandQuantity.split(/[eE]/)[0] ?? '')
          "
          @click="emit('select', item)"
          ><span class="min-w-0"
            ><span class="block break-words"
              >{{ item.locationCode }} ·
              {{ stockStatusLabel(item.stockStatus) }} ·
              {{ item.onHandQuantity }} {{ item.baseUom }}</span
            ><span
              v-if="item.lotNumber"
              class="block break-words text-xs text-muted-foreground"
              >Партия {{ item.lotNumber }} · срок
              {{ item.expiresOn ?? "—" }}</span
            ><span
              v-if="item.serialNumber"
              class="block break-words text-xs text-muted-foreground"
              >Серия {{ item.serialNumber }}</span
            ></span
          ></Button
        >
      </div>
      <div class="flex items-center justify-between gap-3">
        <Button
          variant="outline"
          :disabled="loading || !offset"
          @click="emit('page', Math.max(0, offset - 20))"
          >Назад</Button
        ><span class="text-xs"
          >{{ total ? offset + 1 : 0 }}–{{ Math.min(offset + 20, total) }} из
          {{ total }}</span
        ><Button
          variant="outline"
          :disabled="loading || offset + 20 >= total"
          @click="emit('page', offset + 20)"
          >Далее</Button
        >
      </div>
    </DialogContent></Dialog
  >
</template>
