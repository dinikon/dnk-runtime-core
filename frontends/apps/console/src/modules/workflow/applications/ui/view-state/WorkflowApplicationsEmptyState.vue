<script setup lang="ts">
import { ClipboardList } from "@lucide/vue";

import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
</script>

<template>
  <Empty class="min-h-72">
    <EmptyHeader>
      <EmptyMedia variant="icon">
        <ClipboardList />
      </EmptyMedia>
      <EmptyTitle>No workflow applications</EmptyTitle>
      <EmptyDescription>
        Workflow applications will appear here after the first run is created.
      </EmptyDescription>
    </EmptyHeader>
  </Empty>
</template>
