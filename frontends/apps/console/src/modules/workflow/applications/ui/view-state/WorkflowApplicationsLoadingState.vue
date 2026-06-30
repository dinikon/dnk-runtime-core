<script setup lang="ts">
import { Skeleton } from "@/components/ui/skeleton";

withDefaults(
  defineProps<{
    count?: number;
  }>(),
  {
    count: 1,
  },
);
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
    <div
      v-for="index in count"
      :key="index"
      class="flex min-h-64 flex-col gap-4 rounded-xl border py-6"
    >
      <div class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 px-6">
        <Skeleton class="row-span-2 size-11" />
        <Skeleton class="h-5 w-3/4" />
        <Skeleton class="h-4 w-full" />
      </div>

      <div class="flex flex-col gap-3 px-6">
        <div class="flex gap-2">
          <Skeleton class="h-5 w-20 rounded-full" />
          <Skeleton class="h-5 w-24 rounded-full" />
        </div>

        <div class="grid gap-2">
          <Skeleton class="h-3 w-12" />
          <Skeleton class="h-4 w-full" />
        </div>

        <div class="grid gap-2">
          <Skeleton class="h-3 w-16" />
          <Skeleton class="h-4 w-36" />
        </div>
      </div>
    </div>
  </div>
</template>
