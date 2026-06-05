<script setup lang="ts">
import { RefreshCcw } from "lucide-vue-next";

import { Button } from "@/components/ui/button";
import CommunicationPageHeader from "@/modules/communication/components/CommunicationPageHeader.vue";

defineProps<{
  description: string;
  refreshing?: boolean;
  title: string;
}>();

defineEmits<{
  refresh: [];
}>();
</script>

<template>
  <div
    class="flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between"
  >
    <CommunicationPageHeader :title="title" :description="description" />
    <Button
      type="button"
      variant="outline"
      :disabled="refreshing"
      @click="$emit('refresh')"
    >
      <RefreshCcw class="size-4" :class="{ 'animate-spin': refreshing }" />
      Refresh
    </Button>
  </div>
</template>
