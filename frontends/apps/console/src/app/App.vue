<script setup lang="ts">
import { useColorMode } from "@vueuse/core";
import { computed } from "vue";

import { Toaster } from "@/components/ui/sonner";

const mode = useColorMode({
  initialValue: "auto",
  storageKey: null,
});
const toasterTheme = computed(() => (mode.value === "dark" ? "dark" : "light"));
</script>

<template>
  <RouterView />
  <Toaster rich-colors close-button :theme="toasterTheme" />
</template>
