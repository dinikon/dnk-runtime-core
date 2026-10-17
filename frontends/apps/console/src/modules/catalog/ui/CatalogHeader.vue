<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{
  title: string;
  description: string;
  action?: string;
  disabled?: boolean;
}>();
defineEmits<{ create: [] }>();
</script>
<template>
  <header class="flex flex-wrap items-start justify-between gap-4">
    <div>
      <p
        class="text-xs font-semibold uppercase tracking-widest text-muted-foreground"
      >
        Catalog
      </p>
      <h1 class="mt-1 text-2xl font-semibold">{{ title }}</h1>
      <p class="mt-2 text-sm text-muted-foreground">{{ description }}</p>
    </div>
    <Button v-if="action" :disabled="disabled" @click="$emit('create')">{{
      action
    }}</Button>
  </header>
</template>
