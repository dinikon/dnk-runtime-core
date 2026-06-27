<script setup lang="ts">
import { computed } from "vue";

import { Badge } from "@/components/ui/badge";

const props = defineProps<{
  status: string | null | undefined;
}>();

const normalizedStatus = computed(() => props.status?.toUpperCase() ?? "NONE");

const variant = computed(() => {
  if (
    ["FAILED", "REJECTED", "UNDELIVERED", "EXPIRED", "CANCELED"].includes(
      normalizedStatus.value,
    )
  ) {
    return "destructive";
  }

  if (
    ["ACTIVE", "SENT", "DELIVERED", "OPENED", "SUCCESS"].includes(
      normalizedStatus.value,
    )
  ) {
    return "default";
  }

  if (
    ["DRAFT", "QUEUED", "SENDING", "STARTED"].includes(normalizedStatus.value)
  ) {
    return "secondary";
  }

  return "outline";
});
</script>

<template>
  <Badge :variant="variant">
    {{ normalizedStatus }}
  </Badge>
</template>
