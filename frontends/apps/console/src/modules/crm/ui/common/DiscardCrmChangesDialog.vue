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
defineProps<{ open: boolean }>();
const emit = defineEmits<{ decide: [approved: boolean] }>();
</script>
<template>
  <AlertDialog :open="open" @update:open="!$event && emit('decide', false)">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Отменить несохранённые изменения?</AlertDialogTitle>
        <AlertDialogDescription
          >Изменения полей и связей этой карточки будут
          потеряны.</AlertDialogDescription
        >
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel @click="emit('decide', false)"
          >Продолжить редактирование</AlertDialogCancel
        >
        <Button variant="destructive" @click="emit('decide', true)"
          >Отменить изменения</Button
        >
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
