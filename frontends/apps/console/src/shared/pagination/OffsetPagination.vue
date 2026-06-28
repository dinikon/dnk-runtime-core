<script setup lang="ts">
import { computed } from "vue";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const props = withDefaults(
  defineProps<{
    page: number;
    limit: number;
    total: number;
    disabled?: boolean;
    limitOptions?: number[];
  }>(),
  {
    disabled: false,
    limitOptions: () => [10, 20, 50, 100],
  },
);

const emit = defineEmits<{
  (event: "update:page", value: number): void;
  (event: "update:limit", value: number): void;
}>();

const safeLimit = computed(() => Math.max(1, props.limit));
const safeTotal = computed(() => Math.max(0, props.total));

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(safeTotal.value / safeLimit.value));
});

const normalizedPage = computed(() => {
  return Math.min(Math.max(props.page, 1), totalPages.value);
});

const canGoPrev = computed(() => normalizedPage.value > 1);
const canGoNext = computed(() => normalizedPage.value < totalPages.value);

const from = computed(() => {
  if (safeTotal.value === 0) {
    return 0;
  }

  return (normalizedPage.value - 1) * safeLimit.value + 1;
});

const to = computed(() => {
  if (safeTotal.value === 0) {
    return 0;
  }

  return Math.min(normalizedPage.value * safeLimit.value, safeTotal.value);
});

function goToPage(page: number) {
  const nextPage = Math.min(Math.max(page, 1), totalPages.value);

  emit("update:page", nextPage);
}

function changeLimit(value: unknown) {
  if (typeof value !== "string" && typeof value !== "number") {
    return;
  }

  const nextLimit = Number(value);

  if (!Number.isFinite(nextLimit) || nextLimit <= 0) {
    return;
  }

  emit("update:limit", nextLimit);
  emit("update:page", 1);
}
</script>

<template>
  <div
    class="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between"
  >
    <p class="text-sm text-muted-foreground">
      Showing {{ from }}–{{ to }} of {{ safeTotal }}
    </p>

    <div class="flex flex-wrap items-center gap-2">
      <Select
        :model-value="String(limit)"
        :disabled="disabled"
        @update:model-value="changeLimit"
      >
        <SelectTrigger class="h-9 w-32">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem
            v-for="option in limitOptions"
            :key="option"
            :value="String(option)"
          >
            {{ option }} / page
          </SelectItem>
        </SelectContent>
      </Select>

      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="disabled || !canGoPrev"
        @click="goToPage(normalizedPage - 1)"
      >
        Previous
      </Button>

      <span class="min-w-24 text-center text-sm text-muted-foreground">
        {{ normalizedPage }} / {{ totalPages }}
      </span>

      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="disabled || !canGoNext"
        @click="goToPage(normalizedPage + 1)"
      >
        Next
      </Button>
    </div>
  </div>
</template>
