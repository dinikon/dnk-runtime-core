<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
defineProps<{
  open: boolean;
  title: string;
  loading: boolean;
  busy: boolean;
  error: string;
  canConfirm: boolean;
}>();
defineEmits<{ close: []; confirm: []; retry: [] }>();
</script>
<template>
  <AlertDialog :open="open" @update:open="!$event && !busy && $emit('close')"
    ><AlertDialogContent
      ><AlertDialogHeader
        ><AlertDialogTitle>Отменить связь с товаром?</AlertDialogTitle
        ><AlertDialogDescription
          >Связь «{{ title }}» будет снята со всей группы сопоставлений.
          Публикации и товар сохранятся.</AlertDialogDescription
        ></AlertDialogHeader
      >
      <p v-if="loading" role="status" class="text-sm text-muted-foreground">
        Загружаем актуальную связь…
      </p>
      <Alert v-if="error" variant="destructive"
        ><AlertDescription
          >{{ error
          }}<Button
            type="button"
            variant="outline"
            :disabled="busy || loading"
            @click="$emit('retry')"
            >Обновить данные</Button
          ></AlertDescription
        ></Alert
      >
      <AlertDialogFooter
        ><AlertDialogCancel :disabled="busy">Отмена</AlertDialogCancel
        ><Button
          type="button"
          variant="destructive"
          :disabled="busy || loading || !canConfirm"
          @click="$emit('confirm')"
          >{{ busy ? "Отменяем…" : "Отменить связь" }}</Button
        ></AlertDialogFooter
      >
    </AlertDialogContent></AlertDialog
  >
</template>
