<script setup lang="ts">
import { Toaster } from "@/components/ui/sonner";
</script>

<template>
  <RouterView />
  <Toaster rich-colors close-button />
</template>
