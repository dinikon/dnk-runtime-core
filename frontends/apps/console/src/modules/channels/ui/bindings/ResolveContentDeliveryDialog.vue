<script setup lang="ts">
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

defineProps<{
  open: boolean;
  externalId: string;
  busy: boolean;
  error: string;
}>();
const emit = defineEmits<{ "update:open": [open: boolean]; confirm: [] }>();
</script>

<template>
  <AlertDialog :open="open" @update:open="!busy && emit('update:open', $event)">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle
          >Завершить попытку для товара {{ externalId }}?</AlertDialogTitle
        >
        <AlertDialogDescription>
          Результат останется неподтверждённым. Данные в WooCommerce и уже
          загруженные изображения сохранятся. Новая отправка потребует проверки
          актуального контента. Изображения с неизвестным результатом загрузки
          останутся заблокированными до подтверждения сверкой или выбора другого
          файла.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="busy">Отмена</AlertDialogCancel>
        <Button
          type="button"
          variant="outline"
          :disabled="busy"
          @click="emit('confirm')"
        >
          {{ busy ? "Завершаем…" : "Завершить без подтверждения" }}
        </Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
