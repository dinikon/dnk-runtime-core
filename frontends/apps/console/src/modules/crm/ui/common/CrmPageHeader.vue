<script setup lang="ts">
import { Plus } from "@lucide/vue";
import { Button } from "@/components/ui/button";

defineProps<{
  eyebrow: string;
  title: string;
  description: string;
  actionLabel: string;
}>();
defineEmits<{ create: [] }>();
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-3">
    <div class="flex flex-col gap-1">
      <p class="text-sm text-muted-foreground">{{ eyebrow }}</p>
      <h1 class="text-2xl font-semibold tracking-tight">{{ title }}</h1>
      <p class="text-sm text-muted-foreground">{{ description }}</p>
    </div>
    <Button @click="$emit('create')">
      <Plus data-icon="inline-start" />
      {{ actionLabel }}
    </Button>
  </header>
</template>
