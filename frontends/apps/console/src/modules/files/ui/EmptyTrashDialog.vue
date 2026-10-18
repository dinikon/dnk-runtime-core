<script setup lang="ts">
import { watch } from "vue";
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
import { Spinner } from "@/components/ui/spinner";
const props = defineProps<{ open: boolean; busy: boolean; error: string }>();
defineEmits<{ close: []; confirm: [] }>();
let trigger: HTMLElement | null = null;
watch(
  () => props.open,
  (open) => {
    if (open) trigger = document.activeElement as HTMLElement | null;
  },
  { flush: "sync" },
);
function restoreFocus(event: Event): void {
  event.preventDefault();
  if (trigger?.isConnected && !trigger.matches(":disabled")) trigger.focus();
}
</script>
<template>
  <AlertDialog :open="open" @update:open="!$event && !busy && $emit('close')"
    ><AlertDialogContent
      @escape-key-down="busy && $event.preventDefault()"
      @close-auto-focus="restoreFocus"
    >
      <AlertDialogHeader
        ><AlertDialogTitle>Очистить всю корзину?</AlertDialogTitle
        ><AlertDialogDescription
          >Очистка охватит файлы на всех дисках, включая скрытые фильтрами и
          другими страницами. Удаление выполняется в фоне. Файлы, отправленные
          на удаление, восстановить нельзя. Новые файлы, добавленные в корзину
          после запроса, останутся в ней.</AlertDialogDescription
        ></AlertDialogHeader
      >
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <AlertDialogFooter
        ><AlertDialogCancel :disabled="busy">Отмена</AlertDialogCancel
        ><Button
          variant="destructive"
          :disabled="busy"
          @click="$emit('confirm')"
          ><Spinner v-if="busy" />Очистить корзину</Button
        ></AlertDialogFooter
      >
    </AlertDialogContent></AlertDialog
  >
</template>
