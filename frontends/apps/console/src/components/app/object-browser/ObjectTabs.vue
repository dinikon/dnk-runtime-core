<script setup lang="ts">
import {Database, Loader2} from "lucide-vue-next";

import type {RuntimeObject} from "@/shared/api/schema-registry";

defineProps<{
  objects: RuntimeObject[];
  selectedObjectId: string | null;
  isLoading: boolean;
}>();

defineEmits<{
  select: [object: RuntimeObject];
}>();

function kindLabel(kind: string): string {
  return kind.trim().toLowerCase() === "custom" ? "Custom" : "Standard";
}
</script>

<template>
  <section class="rounded-lg border border-neutral-200 bg-white shadow-sm">
    <div v-if="isLoading" class="flex min-h-12 items-center gap-2 px-4 text-sm text-neutral-400">
      <Loader2 class="size-4 animate-spin"/>
      Loading objects...
    </div>

    <div v-else-if="objects.length === 0" class="flex min-h-12 items-center px-4 text-sm text-neutral-400">
      No objects available.
    </div>

    <div v-else class="flex min-h-12 items-center gap-1 overflow-x-auto px-2 py-2">
      <button
          v-for="object in objects"
          :key="object.id"
          type="button"
          class="inline-flex h-8 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          :class="selectedObjectId === object.id ? 'bg-neutral-900 text-white hover:bg-neutral-800 hover:text-white' : ''"
          @click="$emit('select', object)"
      >
        <Database class="size-4"/>
        <span>{{ object.plural_label }}</span>
        <span
            class="rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase"
            :class="selectedObjectId === object.id ? 'bg-white/15 text-white' : 'bg-neutral-100 text-neutral-400'"
        >
          {{ kindLabel(object.kind) }}
        </span>
      </button>
    </div>
  </section>
</template>
