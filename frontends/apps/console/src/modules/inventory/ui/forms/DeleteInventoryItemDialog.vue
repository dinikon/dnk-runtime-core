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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { InventoryItemDeleteTarget } from "../../model/inventory-item-editor.types";
defineProps<{
  item: InventoryItemDeleteTarget;
  dirty?: boolean;
  pending: boolean;
  uncertain: boolean;
  error: string;
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
      <AlertDialogHeader>
        <AlertDialogTitle>Удалить складскую позицию?</AlertDialogTitle>
        <AlertDialogDescription
          >Позиция, её штрихкоды и упаковки будут удалены без возможности
          восстановления. Позицию, связанную с элементом каталога, удалить
          нельзя.</AlertDialogDescription
        >
      </AlertDialogHeader>
      <p class="break-all font-mono text-sm">SKU: {{ item.sku }}</p>
      <Alert v-if="dirty"
        ><AlertDescription
          >Несохранённые изменения будут потеряны после удаления
          позиции.</AlertDescription
        ></Alert
      >
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="pending" @click="emit('close')"
          >Отмена</AlertDialogCancel
        >
        <Button
          v-if="uncertain"
          type="button"
          variant="outline"
          :disabled="pending"
          @click="emit('check')"
          ><Spinner
            v-if="pending"
            data-icon="inline-start"
            aria-hidden="true"
          />Проверить наличие</Button
        >
        <Button
          v-else
          type="button"
          variant="destructive"
          :disabled="pending"
          @click="emit('confirm')"
          ><Spinner
            v-if="pending"
            data-icon="inline-start"
            aria-hidden="true"
          />{{ pending ? "Удаление…" : "Удалить позицию" }}</Button
        >
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
