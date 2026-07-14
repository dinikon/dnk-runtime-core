<script setup lang="ts">
import { useCurrentUserQuery } from "@/modules/auth/queries/use-current-user-query";

useCurrentUserQuery();
</script>

<template>
  <main class="h-svh min-h-0 w-full overflow-hidden bg-background">
    <RouterView />
  </main>
</template>
