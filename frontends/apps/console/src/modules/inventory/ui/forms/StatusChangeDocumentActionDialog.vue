<script setup lang="ts">
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
defineProps<{
  reason: string;
  targetStatus: string;
  action: "confirm" | "cancel";
  version: number;
  pending: boolean;
  error: string;
  blocked: boolean;
}>();
const emit = defineEmits<{ close: []; confirm: []; check: [] }>();
</script>
<template>
  <AlertDialog :open="true" @update:open="!$event && !pending && emit('close')">
    <AlertDialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :aria-busy="pending"
      @escape-key-down="pending && $event.preventDefault()"
    >
      <AlertDialogHeader
        ><AlertDialogTitle>{{
          action === "confirm"
            ? "Подтвердить план изменения состояния?"
            : "Отменить документ изменения состояния?"
        }}</AlertDialogTitle>
        <AlertDialogDescription
          >{{
            action === "confirm"
              ? "План, новое состояние и причина будут зафиксированы. Редактирование станет недоступно. Физические остатки не изменятся."
              : "Документ и строки останутся в истории. Простая отмена разрешена только до фактического исполнения."
          }}
          Версия: {{ version }}.</AlertDialogDescription
        ></AlertDialogHeader
      >
      <p class="text-sm">
        Новое состояние: {{ stockStatusLabel(targetStatus) }}
      </p>
      <p class="whitespace-pre-wrap break-words text-sm">
        <strong>Причина изменения состояния:</strong> {{ reason }}
      </p>
      <p v-if="error" role="alert" class="text-sm text-destructive">
        {{ error }}
      </p>
      <AlertDialogFooter
        ><AlertDialogCancel :disabled="pending" @click="emit('close')"
          >Закрыть</AlertDialogCancel
        >
        <Button
          v-if="blocked"
          variant="outline"
          :disabled="pending"
          @click="emit('check')"
          >Проверить состояние</Button
        >
        <Button
          v-else
          :variant="action === 'cancel' ? 'destructive' : 'default'"
          :disabled="pending"
          @click="emit('confirm')"
          >{{
            pending
              ? "Выполнение…"
              : action === "confirm"
                ? "Подтвердить план"
                : "Отменить документ"
          }}</Button
        >
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
