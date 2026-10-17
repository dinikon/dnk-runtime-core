<script setup lang="ts">
import { useColorMode } from "@vueuse/core";
import { computed, watch } from "vue";
import { useUserStore } from "@/app/stores/user";

import { Toaster } from "@/components/ui/sonner";

const mode = useColorMode({
  initialValue: "auto",
  storageKey: null,
});
const user = useUserStore();
watch(
  () => user.user?.interface_theme,
  (theme) => {
    mode.value = theme === "light" || theme === "dark" ? theme : "auto";
  },
  { immediate: true },
);
const toasterTheme = computed(() => (mode.value === "dark" ? "dark" : "light"));
</script>

<template>
  <RouterView />
  <Toaster rich-colors close-button :theme="toasterTheme" />
</template>
