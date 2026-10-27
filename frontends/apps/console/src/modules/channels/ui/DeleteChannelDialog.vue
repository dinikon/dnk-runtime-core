<script setup lang="ts">
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
defineProps<{ open: boolean; name: string; busy: boolean; error: string }>();
const emit = defineEmits<{ "update:open": [open: boolean]; confirm: [] }>();
</script>
<template>
  <AlertDialog :open="open" @update:open="!busy && emit('update:open', $event)"
    ><AlertDialogContent
      ><AlertDialogHeader
        ><AlertDialogTitle>Удалить канал «{{ name }}»?</AlertDialogTitle
        ><AlertDialogDescription
          >Подключение и сохранённый доступ будут удалены. Магазин можно будет
          подключить снова.</AlertDialogDescription
        ></AlertDialogHeader
      ><Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      ><AlertDialogFooter
        ><AlertDialogCancel :disabled="busy">Отмена</AlertDialogCancel
        ><AlertDialogAction :disabled="busy" @click.prevent="emit('confirm')">{{
          busy ? "Удаляем…" : "Удалить канал"
        }}</AlertDialogAction></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
