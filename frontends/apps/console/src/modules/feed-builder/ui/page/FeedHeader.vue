<script setup lang="ts">
import { ChevronRight, Rss, Archive } from "@lucide/vue";
import { Button } from "@/components/ui/button";
defineProps<{ title: string; archivable: boolean; busy: boolean }>();
defineEmits<{ back: []; archive: [] }>();
</script>
<template>
  <div class="flex min-w-0 flex-1 items-center justify-between gap-2">
    <nav class="flex min-w-0 items-center gap-1" aria-label="Навигация фида">
      <Button type="button" variant="ghost" size="sm" @click="$emit('back')"
        ><Rss data-icon="inline-start" />Фиды</Button
      >
      <ChevronRight
        class="size-4 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
      <span class="truncate text-sm" :title="title" aria-current="page">{{
        title
      }}</span>
    </nav>
    <Button
      v-if="archivable"
      type="button"
      variant="ghost"
      size="sm"
      :disabled="busy"
      @click="$emit('archive')"
      ><Archive data-icon="inline-start" /><span class="hidden sm:inline"
        >В архив</span
      ><span class="sr-only sm:hidden">В архив</span></Button
    >
  </div>
</template>
