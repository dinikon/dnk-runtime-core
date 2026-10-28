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
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
defineProps<{
  open: boolean;
  title: string;
  pending: boolean;
  error: string;
}>();
const emit = defineEmits<{ "update:open": [value: boolean]; confirm: [] }>();
</script>
<template>
  <AlertDialog
    :open="open"
    @update:open="!pending && emit('update:open', $event)"
    ><AlertDialogContent
      ><AlertDialogHeader
        ><AlertDialogTitle>Удалить вариант «{{ title }}»?</AlertDialogTitle
        ><AlertDialogDescription
          >Будут удалены собственные данные и назначения изображений этой
          позиции. Родительская карточка и остальные варианты
          сохранятся.</AlertDialogDescription
        ></AlertDialogHeader
      ><Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      ><AlertDialogFooter
        ><AlertDialogCancel :disabled="pending">Отмена</AlertDialogCancel
        ><Button
          variant="destructive"
          :disabled="pending"
          @click="emit('confirm')"
          >{{ pending ? "Удаляем…" : "Удалить вариант" }}</Button
        ></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
