<script setup lang="ts">
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
import { Spinner } from "@/components/ui/spinner";

defineProps<{
  open: boolean;
  label: string;
  entityName: string;
  pending: boolean;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  confirm: [];
}>();
</script>

<template>
  <AlertDialog :open="open" @update:open="emit('update:open', $event)">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Удалить {{ label }}?</AlertDialogTitle>
        <AlertDialogDescription>
          Запись «{{ entityName }}» будет удалена без возможности
          восстановления.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="pending">Отмена</AlertDialogCancel>
        <Button
          variant="destructive"
          :disabled="pending"
          @click="emit('confirm')"
        >
          <Spinner v-if="pending" data-icon="inline-start" />
          Удалить
        </Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
