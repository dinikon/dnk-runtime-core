<script setup lang="ts">
import type { Component } from "vue";
import { useId } from "vue";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

defineProps<{
  title: string;
  description?: string;
  icon?: Component;
  primaryActionLabel?: string;
  secondaryActionLabel?: string;
  primaryDisabled?: boolean;
  secondaryDisabled?: boolean;
}>();

const emit = defineEmits<{
  primaryAction: [];
  secondaryAction: [];
}>();

const id = useId();
</script>

<template>
  <Empty
    role="region"
    :aria-labelledby="`${id}-title`"
    :aria-describedby="description ? `${id}-description` : undefined"
    class="@container/empty-state border p-6 md:p-6"
  >
    <EmptyHeader class="max-w-2xl">
      <EmptyMedia v-if="icon" variant="outline" class="mb-4" aria-hidden="true">
        <component :is="icon" />
      </EmptyMedia>
      <EmptyTitle :id="`${id}-title`" as="h2" size="lg">
        {{ title }}
      </EmptyTitle>
      <EmptyDescription v-if="description" :id="`${id}-description`">
        {{ description }}
      </EmptyDescription>
    </EmptyHeader>
    <EmptyContent
      v-if="primaryActionLabel || secondaryActionLabel"
      class="max-w-none"
    >
      <div
        class="flex w-full flex-col gap-3 @sm/empty-state:w-auto @sm/empty-state:flex-row"
      >
        <Button
          v-if="primaryActionLabel"
          type="button"
          :disabled="primaryDisabled"
          class="w-full @sm/empty-state:w-auto"
          @click="emit('primaryAction')"
        >
          {{ primaryActionLabel }}
        </Button>
        <Button
          v-if="secondaryActionLabel"
          type="button"
          variant="outline"
          :disabled="secondaryDisabled"
          class="w-full @sm/empty-state:w-auto"
          @click="emit('secondaryAction')"
        >
          {{ secondaryActionLabel }}
        </Button>
      </div>
    </EmptyContent>
  </Empty>
</template>
