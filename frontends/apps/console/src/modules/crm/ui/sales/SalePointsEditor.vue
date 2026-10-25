<script setup lang="ts">
import { computed } from "vue";
import {
  validateContactPoints,
  PhoneContactPointsField,
  EmailContactPointsField,
} from "@/modules/contact-points";
import type {
  ContactPointArrays,
  ContactPointLabel,
} from "@/modules/contact-points";
const props = defineProps<{
  modelValue: ContactPointArrays;
  labels: ContactPointLabel[];
  disabled?: boolean;
  loading?: boolean;
  error?: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: ContactPointArrays];
}>();
const errors = computed(() => ({
  ...validateContactPoints(props.modelValue.phones, "phone"),
  ...validateContactPoints(props.modelValue.emails, "email"),
}));
</script>
<template>
  <div class="flex flex-col gap-5">
    <PhoneContactPointsField
      :model-value="modelValue.phones"
      :attempted="true"
      :errors="errors"
      :labels="labels.filter((l) => l.type === 'phone')"
      :disabled="disabled"
      :labels-loading="loading"
      :labels-error="error"
      @update:model-value="
        emit('update:modelValue', { ...props.modelValue, phones: $event })
      "
    /><EmailContactPointsField
      :model-value="modelValue.emails"
      :attempted="true"
      :errors="errors"
      :labels="labels.filter((l) => l.type === 'email')"
      :disabled="disabled"
      :labels-loading="loading"
      :labels-error="error"
      @update:model-value="
        emit('update:modelValue', { ...props.modelValue, emails: $event })
      "
    />
  </div>
</template>
