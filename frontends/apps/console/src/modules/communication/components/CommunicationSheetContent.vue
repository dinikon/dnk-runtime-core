<script setup lang="ts">
import {
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

defineProps<{
  description: string;
  maxWidthClass?: string;
  title: string;
}>();
</script>

<template>
  <SheetContent
    :class="
      maxWidthClass ??
      'w-[min(34rem,100vw)] gap-2 overflow-y-auto p-4 sm:max-w-xl'
    "
  >
    <SheetHeader class="gap-1 p-0 pr-8">
      <SheetTitle>{{ title }}</SheetTitle>
      <SheetDescription>
        {{ description }}
      </SheetDescription>
    </SheetHeader>

    <slot />
  </SheetContent>
</template>
