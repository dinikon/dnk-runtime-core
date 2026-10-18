<script setup lang="ts">
import { Badge } from "@/components/ui/badge";
import { verificationLabel } from "../model/channels.presentation";
defineProps<{
  status: string | null;
  paused?: boolean | null;
  archived?: boolean;
}>();
</script>
<template>
  <Badge :variant="status === 'error' ? 'destructive' : 'secondary'">{{
    archived ? "Архив" : paused ? "Приостановлено" : verificationLabel(status)
  }}</Badge>
</template>
