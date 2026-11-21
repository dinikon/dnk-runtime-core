<script setup lang="ts">
import { ArrowLeft, MapPin } from "@lucide/vue";
import { Button } from "@/components/ui/button";
defineProps<{ code?: string; pending: boolean; locationsDisabled: boolean }>();
const emit = defineEmits<{ back: []; locations: [] }>();
</script>
<template>
  <header class="flex min-w-0 flex-wrap items-start gap-4">
    <Button
      type="button"
      variant="outline"
      :disabled="pending"
      @click="emit('back')"
      ><ArrowLeft data-icon="inline-start" />Назад</Button
    >
    <div class="flex min-w-0 flex-1 flex-col gap-1">
      <h1 class="text-xl font-semibold">Редактирование склада</h1>
      <p v-if="code" class="break-all font-mono text-sm">{{ code }}</p>
      <p class="text-sm text-muted-foreground">
        Код, название и административная активность склада.
      </p>
    </div>
    <Button
      type="button"
      variant="outline"
      :disabled="pending || locationsDisabled"
      @click="emit('locations')"
      ><MapPin data-icon="inline-start" />Локации</Button
    >
  </header>
</template>
