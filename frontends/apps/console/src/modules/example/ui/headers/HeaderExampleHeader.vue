<script setup lang="ts">
defineProps<{ title: string }>();
</script>

<template>
  <p class="text-sm font-medium">{{ title }}</p>
</template>
