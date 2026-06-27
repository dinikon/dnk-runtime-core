<script setup lang="ts">
defineProps<{
  title: string;
  description: string;
}>();
</script>

<template>
  <div class="grid gap-1">
    <h2 class="text-lg font-semibold tracking-normal">{{ title }}</h2>
    <p class="max-w-3xl text-sm text-muted-foreground">
      {{ description }}
    </p>
  </div>
</template>
