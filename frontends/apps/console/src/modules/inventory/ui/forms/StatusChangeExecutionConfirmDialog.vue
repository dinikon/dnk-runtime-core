<script setup lang="ts">
import type { StatusChangePreview } from "../../model/status-change-preview.types";
import StatusChangePreviewPanel from "../results/StatusChangePreview.vue";
import { stockStatusLabel } from "../../model/stock-accounting.constants";
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
  reason: string;
  targetStatus: string;
  preview: StatusChangePreview | null;
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
        ><AlertDialogTitle>Изменить состояние и провести?</AlertDialogTitle
        ><AlertDialogDescription
          >План версии {{ version }}. Фактических строк: {{ count }}. Количество
          уменьшится в исходном состоянии и увеличится в новом. Общее количество
          сохранится. Простая отмена документа после исполнения
          недоступна.</AlertDialogDescription
        ></AlertDialogHeader
      >
      <StatusChangePreviewPanel v-if="preview" :preview="preview" />
      <p class="text-sm">
        Новое состояние: {{ stockStatusLabel(targetStatus) }}
      </p>
      <p class="whitespace-pre-wrap break-words text-sm">
        <strong>Причина изменения состояния:</strong> {{ reason }}
      </p>
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
              : "Изменить состояние и провести"
        }}</Button></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
