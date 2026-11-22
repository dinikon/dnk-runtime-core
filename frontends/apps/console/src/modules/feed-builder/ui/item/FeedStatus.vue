<script setup lang="ts">
import { Badge } from "@/components/ui/badge";
import { feedStatuses } from "../../model/feed.constants";
import type { FeedStatus } from "../../model/feed.types";
defineProps<{ status: FeedStatus }>();
</script>
<template>
  <Badge :variant="status === 'ACTIVE' ? 'default' : 'secondary'">{{
    feedStatuses[status]
  }}</Badge>
</template>
