<script setup lang="ts">
import { ref, watch } from "vue";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { PriceList } from "../../model/types";

const props = defineProps<{ open: boolean; priceList: PriceList | null; pending: boolean }>();
const emit = defineEmits<{ "update:open": [value: boolean]; confirm: [title: string] }>();
const confirmation = ref("");
watch(() => props.open, (open) => { if (!open) confirmation.value = ""; });
</script>

<template>
  <AlertDialog :open="open" @update:open="emit('update:open', $event)">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Удалить прайс-лист окончательно?</AlertDialogTitle>
        <AlertDialogDescription>Офферы, история цен и запуски будут удалены без возможности восстановления.</AlertDialogDescription>
      </AlertDialogHeader>
      <Field>
        <FieldLabel for="delete-price-list-confirmation">Введите «{{ priceList?.title }}»</FieldLabel>
        <Input id="delete-price-list-confirmation" v-model="confirmation" autocomplete="off" />
        <FieldDescription>Удаление доступно только для архивного прайс-листа.</FieldDescription>
      </Field>
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="pending">Отмена</AlertDialogCancel>
        <AlertDialogAction class="bg-destructive text-destructive-foreground hover:bg-destructive/90" :disabled="pending || confirmation !== priceList?.title" @click="emit('confirm', confirmation)">Удалить окончательно</AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
