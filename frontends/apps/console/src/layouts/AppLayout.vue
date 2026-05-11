<script setup lang="ts">
import {ConsoleSidebar} from "@/features/app-shell";
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-neutral-100 text-neutral-900">
    <ConsoleSidebar/>

    <main class="flex min-w-0 flex-1 flex-col gap-3 p-4">
      <header class="flex min-h-10 items-center gap-3 px-1">
        <slot name="header"/>
      </header>

      <slot/>
    </main>
  </div>
</template>
