<script setup lang="ts">
import {ObjectBrowserPage} from "@/features/object-browser";
import {AppLayout} from "@/layouts";
</script>

<template>
  <AppLayout>
    <template #header>
      <h1 class="truncate text-base font-semibold text-neutral-800">Objects</h1>
    </template>

    <ObjectBrowserPage/>
  </AppLayout>
</template>
