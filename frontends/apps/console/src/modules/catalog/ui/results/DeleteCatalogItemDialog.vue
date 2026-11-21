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
import type { CatalogListItem } from "../../model/catalog.types";

defineProps<{ item: CatalogListItem; pending: boolean; error: string }>();
const emit = defineEmits<{ close: []; confirm: [] }>();
</script>

<template>
  <AlertDialog :open="true" @update:open="!$event && !pending && emit('close')">
    <AlertDialogContent>
      <AlertDialogHeader
        ><AlertDialogTitle>Удалить товар?</AlertDialogTitle
        ><AlertDialogDescription
          >«{{ item.title ?? item.sku ?? "Без перевода" }}» и все его варианты
          будут удалены. Восстановить их будет нельзя.</AlertDialogDescription
        ></AlertDialogHeader
      >
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <AlertDialogFooter
        ><AlertDialogCancel :disabled="pending" @click="emit('close')"
          >Отмена</AlertDialogCancel
        ><Button
          type="button"
          variant="destructive"
          :disabled="pending"
          @click="emit('confirm')"
          ><Spinner
            v-if="pending"
            data-icon="inline-start"
            aria-hidden="true"
          />{{ pending ? "Удаление…" : "Удалить товар" }}</Button
        ></AlertDialogFooter
      >
    </AlertDialogContent>
  </AlertDialog>
</template>
