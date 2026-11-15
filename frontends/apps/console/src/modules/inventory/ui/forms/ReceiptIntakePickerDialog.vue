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
import type {
  IntakeReference,
  ReceiptReferenceKind,
} from "../../model/receipt-posting.types";
defineProps<{
  kind: ReceiptReferenceKind;
  search: string;
  items: readonly IntakeReference[];
  loading: boolean;
  error: string;
  offset: number;
  total: number;
}>();
const emit = defineEmits<{
  close: [];
  search: [value: string];
  select: [value: IntakeReference];
  page: [offset: number];
  retry: [];
}>();
const labels: Record<ReceiptReferenceKind, string> = {
  locations: "Выбор локации",
  lots: "Выбор партии",
  serials: "Выбор серийного экземпляра",
};
</script>
<template>
  <Dialog :open="true" @update:open="!$event && emit('close')"
    ><DialogContent class="max-h-[calc(100dvh-2rem)] overflow-y-auto">
      <DialogHeader
        ><DialogTitle>{{ labels[kind] }}</DialogTitle
        ><DialogDescription>{{
          kind === "serials"
            ? "Показаны экземпляры SKU без положительного остатка в tenant."
            : "Серверный поиск внутри склада или SKU строки документа."
        }}</DialogDescription></DialogHeader
      >
      <Input
        :model-value="search"
        type="search"
        aria-label="Поиск варианта приёмки"
        @update:model-value="emit('search', String($event))"
      />
      <p v-if="loading" role="status">Поиск…</p>
      <div v-else-if="error" role="alert" class="text-sm text-destructive">
        {{ error
        }}<Button variant="outline" @click="emit('retry')"
          >Повторить поиск</Button
        >
      </div>
      <div v-else class="max-h-80 overflow-y-auto rounded-md border">
        <p v-if="!items.length" class="p-3 text-sm text-muted-foreground">
          Подходящих вариантов нет.
        </p>
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="block w-full break-words border-b p-3 text-left text-sm hover:bg-muted focus-visible:bg-muted"
          @click="emit('select', item)"
        >
          <span class="font-medium">{{ item.label }}</span
          ><span
            v-if="item.lotNumber"
            class="mt-1 block text-xs text-muted-foreground"
            >Партия {{ item.lotNumber }} · срок
            {{ item.expiresOn ?? "не заполнен" }}</span
          >
        </button>
      </div>
      <div class="flex items-center justify-between gap-2">
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
