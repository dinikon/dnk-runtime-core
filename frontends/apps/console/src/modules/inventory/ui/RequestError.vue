<script setup lang="ts">
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
defineProps<{ message: string; retry?: boolean; pending?: boolean }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <Alert variant="destructive" role="alert"
    ><AlertTitle>Не удалось выполнить операцию</AlertTitle
    ><AlertDescription
      ><p>{{ message }}</p>
      <Button
        v-if="retry"
        type="button"
        variant="outline"
        :disabled="pending"
        @click="$emit('retry')"
        >Повторить</Button
      ></AlertDescription
    ></Alert
  >
</template>
