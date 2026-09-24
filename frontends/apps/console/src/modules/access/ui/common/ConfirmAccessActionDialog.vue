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

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    description: string;
    actionLabel: string;
    pending: boolean;
    error?: string;
    actionVariant?: "default" | "destructive";
    actionDisabled?: boolean;
    blockedMessage?: string;
  }>(),
  {
    actionVariant: "destructive",
    actionDisabled: false,
    blockedMessage: "",
  },
);
const emit = defineEmits<{
  "update:open": [value: boolean];
  confirm: [];
}>();

function updateOpen(value: boolean) {
  if (!value && props.pending) return;
  emit("update:open", value);
}
</script>

<template>
  <AlertDialog :open="open" @update:open="updateOpen">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{{ title }}</AlertDialogTitle>
        <AlertDialogDescription>{{ description }}</AlertDialogDescription>
      </AlertDialogHeader>
      <Alert v-if="error" variant="destructive">
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>
      <Alert v-if="blockedMessage" variant="destructive">
        <AlertDescription>{{ blockedMessage }}</AlertDescription>
      </Alert>
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="pending">Отмена</AlertDialogCancel>
        <Button
          :variant="actionVariant"
          :disabled="pending || actionDisabled"
          @click="emit('confirm')"
        >
          {{ pending ? "Выполняется…" : actionLabel }}
        </Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
