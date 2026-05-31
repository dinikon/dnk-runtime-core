<script setup lang="ts">
import { AppLayout } from "@/layouts";
</script>

<template>
  <AppLayout>
    <template #header>
      <h1 class="truncate text-base font-semibold">Contacts</h1>
    </template>

    <div class="rounded-lg border bg-card p-6 text-sm text-muted-foreground">
      Contacts workspace is available after authentication.
    </div>
  </AppLayout>
</template>
