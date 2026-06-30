<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";

defineProps<{
  message: string;
}>();
</script>

<template>
  <Alert variant="destructive">
    <AlertDescription>
      {{ message }}
    </AlertDescription>
  </Alert>
</template>
