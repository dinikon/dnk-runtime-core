<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
defineProps<{ state: "loading" | "error" | "ready"; label: string }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <p
    v-if="state === 'loading'"
    role="status"
    class="text-sm text-muted-foreground"
  >
    Загрузка: {{ label }}…
  </p>
  <Alert v-else-if="state === 'error'" variant="destructive"
    ><AlertTitle>Не удалось загрузить {{ label }}</AlertTitle
    ><AlertDescription
      ><Button
        type="button"
        variant="outline"
        class="min-h-11"
        @click="$emit('retry')"
        >Повторить загрузку</Button
      ></AlertDescription
    ></Alert
  >
</template>
