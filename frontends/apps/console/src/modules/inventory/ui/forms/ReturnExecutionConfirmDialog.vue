<script setup lang="ts">
import type { ReturnPreview } from "../../model/return-preview.types";
import ReturnPreviewPanel from "../results/ReturnPreview.vue";
import { returnDirectionLabel } from "../../model/return-origin.types";
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
  direction: string;
  preview: ReturnPreview | null;
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
        ><AlertDialogTitle>Провести возврат?</AlertDialogTitle
        ><AlertDialogDescription
          >План версии {{ version }}. Фактических строк: {{ count }}. Количество
          {{
            direction === "FROM_RECIPIENT"
              ? "увеличится по выбранным адресам и состояниям приёмки."
              : "уменьшится в выбранных исходных позициях."
          }}
          Простая отмена документа после исполнения
          недоступна.</AlertDialogDescription
        ></AlertDialogHeader
      >
      <ReturnPreviewPanel v-if="preview" :preview="preview" />
      <p class="text-sm">Направление: {{ returnDirectionLabel(direction) }}</p>
      <p class="whitespace-pre-wrap break-words text-sm">
        <strong>Причина возврата:</strong> {{ reason }}
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
              : "Провести возврат"
        }}</Button></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
