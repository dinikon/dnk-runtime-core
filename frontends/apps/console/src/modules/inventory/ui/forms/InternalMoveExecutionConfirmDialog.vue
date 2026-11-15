<script setup lang="ts">
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogFooter,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import type { InternalMoveAllocation } from "../../model/internal-move-posting.types";
defineProps<{
  rows: readonly InternalMoveAllocation[];
  version: number;
  count: number;
  pending: boolean;
  uncertain: boolean;
  error: string;
}>();
const emit = defineEmits<{ close: []; confirm: [] }>();
</script>
<template>
  <AlertDialog :open="true" @update:open="!$event && !pending && emit('close')"
    ><AlertDialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :aria-busy="pending"
      @escape-key-down="pending && $event.preventDefault()"
      ><AlertDialogHeader
        ><AlertDialogTitle>Переместить товар и провести?</AlertDialogTitle
        ><AlertDialogDescription
          >План версии {{ version }}. Фактических строк: {{ count }}. Расход
          источников и приход назначений будут сохранены вместе. Общее
          количество в складе сохранится. Простая отмена документа после
          исполнения недоступна.</AlertDialogDescription
        ></AlertDialogHeader
      >
      <ul class="space-y-2 text-sm">
        <li v-for="row in rows" :key="row.key" class="break-words">
          {{ row.sku }} · {{ row.source?.locationCode }} →
          {{ row.destination?.code }} · {{ row.quantity }} {{ row.uom
          }}<span v-if="row.source?.serialNumber">
            · {{ row.source.serialNumber }}</span
          >
        </li>
      </ul>
      <p v-if="error" role="alert" class="text-sm text-destructive">
        {{ error }}
      </p>
      <p v-if="uncertain" class="text-sm text-muted-foreground">
        Результат предыдущего запроса неизвестен. Повтор использует прежний ключ
        и исходный состав.
      </p>
      <AlertDialogFooter
        ><AlertDialogCancel :disabled="pending" @click="emit('close')"
          >Вернуться к форме</AlertDialogCancel
        ><Button :disabled="pending" @click="emit('confirm')">{{
          pending
            ? "Проведение…"
            : uncertain
              ? "Повторить исходную команду"
              : "Переместить и провести"
        }}</Button></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
