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
defineProps<{
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
        ><AlertDialogTitle>Выдать товар и провести?</AlertDialogTitle
        ><AlertDialogDescription
          >План версии {{ version }}. Фактических строк: {{ count }}. Физическое
          количество выбранных позиций уменьшится, а движение сохранится в
          истории. Простая отмена документа после исполнения
          недоступна.</AlertDialogDescription
        ></AlertDialogHeader
      >
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
              : "Выдать и провести"
        }}</Button></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
