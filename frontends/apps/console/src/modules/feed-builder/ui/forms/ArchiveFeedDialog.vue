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
  name: string;
  code: string;
  busy: boolean;
  error: string;
  conflicted: boolean;
}>();
const emit = defineEmits<{ "update:open": [open: boolean]; confirm: [] }>();
</script>
<template>
  <AlertDialog :open="open" @update:open="!busy && emit('update:open', $event)">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Архивировать «{{ name }}»?</AlertDialogTitle>
        <AlertDialogDescription
          >Фид останется в архиве только для просмотра. Код «{{ code }}»
          останется занят. Несохранённые изменения не будут
          применены.</AlertDialogDescription
        >
      </AlertDialogHeader>
      <Alert v-if="error" variant="destructive"
        ><AlertDescription
          >{{ error
          }}{{
            conflicted ? " Закройте окно и проверьте актуальные данные." : ""
          }}</AlertDescription
        ></Alert
      >
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="busy">Отмена</AlertDialogCancel>
        <Button
          type="button"
          variant="destructive"
          :disabled="busy || conflicted"
          @click="emit('confirm')"
          >{{ busy ? "Архивируем…" : "Архивировать" }}</Button
        >
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
