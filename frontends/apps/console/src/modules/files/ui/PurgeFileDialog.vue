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
import { Spinner } from "@/components/ui/spinner";
import type { FileItem } from "../model/types";
defineProps<{ file: FileItem | null; busy: boolean; error: string }>();
defineEmits<{ close: []; confirm: [] }>();
</script>
<template>
  <AlertDialog :open="!!file" @update:open="!$event && !busy && $emit('close')"
    ><AlertDialogContent @escape-key-down="busy && $event.preventDefault()"
      ><AlertDialogHeader
        ><AlertDialogTitle>Удалить файл навсегда?</AlertDialogTitle
        ><AlertDialogDescription class="break-words"
          ><span class="block font-medium text-foreground">{{
            file?.name
          }}</span
          >Все версии файла будут окончательно удалены в фоне. Восстановить файл
          после подтверждения нельзя.</AlertDialogDescription
        ></AlertDialogHeader
      ><Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      ><AlertDialogFooter
        ><AlertDialogCancel :disabled="busy">Отмена</AlertDialogCancel
        ><Button
          variant="destructive"
          :disabled="busy"
          @click="$emit('confirm')"
          ><Spinner v-if="busy" />Удалить навсегда</Button
        ></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
