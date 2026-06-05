<script setup lang="ts">
import type { AcceptableValue } from "reka-ui";

import { NativeSelect } from "@/components/ui/native-select";

type CommunicationSelectModelValue = AcceptableValue | AcceptableValue[];

defineProps<{
  disabled?: boolean;
  id?: string;
  modelValue?: CommunicationSelectModelValue;
  required?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: CommunicationSelectModelValue];
}>();

function handleUpdateModelValue(
  value: CommunicationSelectModelValue | undefined,
) {
  if (value === undefined) {
    return;
  }

  emit("update:modelValue", value);
}
</script>

<template>
  <div class="w-full [&>[data-slot=native-select-wrapper]]:w-full">
    <NativeSelect
      :id="id"
      class="w-full"
      :disabled="disabled"
      :model-value="modelValue"
      :required="required"
      @update:model-value="handleUpdateModelValue"
    >
      <slot />
    </NativeSelect>
  </div>
</template>
