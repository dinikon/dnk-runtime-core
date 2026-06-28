<script setup lang="ts">
import { Button } from "@/components/ui/button";

defineProps<{
  cancelLabel: string;
  confirmLabel: string;
  applyDisabled?: boolean;
}>();

defineEmits<{
  (event: "cancel"): void;
  (event: "apply"): void;
}>();
</script>

<template>
  <div class="grid grid-cols-2 gap-2 p-3">
    <Button type="button" variant="outline" @click="$emit('cancel')">
      {{ cancelLabel }}
    </Button>
    <Button type="button" :disabled="applyDisabled" @click="$emit('apply')">
      {{ confirmLabel }}
    </Button>
  </div>
</template>
