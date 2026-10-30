<script setup lang="ts">
import { Cable, ChevronRight } from "@lucide/vue";
import { Button } from "@/components/ui/button";
defineProps<{ title: string; channelName: string; busy: boolean }>();
defineEmits<{ channels: []; publications: [] }>();
</script>
<template>
  <nav
    class="flex min-w-0 flex-1 items-center gap-1"
    aria-label="Навигация публикации"
  >
    <Button
      type="button"
      variant="ghost"
      size="sm"
      class="shrink-0"
      aria-label="Подключения"
      :disabled="busy"
      @click="$emit('channels')"
      ><Cable data-icon="inline-start" /><span class="hidden xl:inline"
        >Подключения</span
      ></Button
    >
    <ChevronRight
      class="size-4 shrink-0 text-muted-foreground"
      aria-hidden="true"
    />
    <Button
      type="button"
      variant="ghost"
      size="sm"
      class="min-w-0 max-w-36 shrink"
      aria-label="Все публикации"
      :title="channelName"
      :disabled="busy"
      @click="$emit('publications')"
      ><span class="truncate">{{ channelName }}</span></Button
    >
    <ChevronRight
      class="size-4 shrink-0 text-muted-foreground"
      aria-hidden="true"
    />
    <span class="truncate text-sm" :title="title" aria-current="page">{{
      title
    }}</span>
  </nav>
</template>
