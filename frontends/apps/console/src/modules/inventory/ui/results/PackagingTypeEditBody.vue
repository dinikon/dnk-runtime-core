<script setup lang="ts">
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
defineProps<{
  loading: boolean;
  error: string;
  canRetry: boolean;
  retryPending: boolean;
  refreshing: boolean;
}>();
const emit = defineEmits<{ retry: [] }>();
</script>
<template>
  <div class="flex flex-col gap-4" :aria-busy="loading || refreshing">
    <Alert v-if="error" variant="destructive">
      <AlertTitle>Не удалось загрузить тип тары</AlertTitle>
      <AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
      >
        <span>{{ error }}</span>
        <Button
          v-if="canRetry"
          type="button"
          variant="outline"
          size="sm"
          :disabled="retryPending"
          @click="emit('retry')"
          >Повторить загрузку</Button
        >
      </AlertDescription>
    </Alert>
    <div
      v-if="loading"
      class="flex flex-col gap-5"
      role="status"
      aria-label="Загрузка типа тары"
    >
      <Skeleton v-for="field in 3" :key="field" class="h-20 w-full" />
    </div>
    <p v-if="refreshing" role="status" class="text-sm text-muted-foreground">
      Обновление данных…
    </p>
    <slot />
  </div>
</template>
