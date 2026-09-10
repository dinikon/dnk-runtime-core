<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <div class="grid gap-1 text-center">
    <slot name="icon" />
    <h1 class="text-base font-semibold leading-none tracking-normal">
      {{ title }}
    </h1>
    <p v-if="description" class="text-sm text-muted-foreground">
      {{ description }}
    </p>
    <slot />
  </div>
</template>
