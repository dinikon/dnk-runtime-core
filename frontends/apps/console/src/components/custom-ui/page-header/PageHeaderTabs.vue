<script setup lang="ts">
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { PageHeaderTab } from "./page-header.types";

withDefaults(
  defineProps<{
    modelValue: string;
    items: readonly PageHeaderTab[];
    ariaLabel?: string;
  }>(),
  { ariaLabel: "Profile sections" },
);
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <Tabs
    :model-value="modelValue"
    class="min-w-0"
    @update:model-value="emit('update:modelValue', String($event))"
  >
    <div
      class="min-w-0 overflow-x-auto [scrollbar-width:none]"
      data-slot="page-header-tabs-scroll"
    >
      <TabsList variant="line" :aria-label="ariaLabel">
        <TabsTrigger
          v-for="item in items"
          :key="item.value"
          :value="item.value"
          variant="line"
          >{{ item.label }}</TabsTrigger
        >
      </TabsList>
    </div>
  </Tabs>
</template>
