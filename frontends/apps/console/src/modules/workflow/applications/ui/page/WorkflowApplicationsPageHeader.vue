<script setup lang="ts">
import { Plus } from "@lucide/vue";

import { Button } from "@/components/ui/button";

const emit = defineEmits<{
  (event: "create"): void;
}>();
</script>

<template>
  <header
    class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"
  >
    <div class="grid gap-1">
      <h2 class="text-lg font-semibold tracking-normal">
        Workflow applications
      </h2>
      <p class="text-sm text-muted-foreground">
        Create and manage workflow apps with their draft definitions.
      </p>
    </div>

    <Button type="button" @click="emit('create')">
      <Plus data-icon="inline-start" />
      Create
    </Button>
  </header>
</template>
