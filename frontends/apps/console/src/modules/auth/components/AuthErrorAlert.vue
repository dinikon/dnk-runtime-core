<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";

defineProps<{
  message: string | null;
}>();
</script>

<template>
  <Alert v-if="message" variant="destructive">
    <AlertDescription>{{ message }}</AlertDescription>
  </Alert>
</template>
