<script setup lang="ts">
import ContactPointsField from "./ContactPointsField.vue";
import type {
  ContactPointsFieldProps,
  ContactPointDraft,
} from "../model/types";
defineProps<ContactPointsFieldProps>();
const emit = defineEmits<{
  "update:modelValue": [value: ContactPointDraft[]];
  "validation-change": [valid: boolean];
}>();
</script>
<template>
  <ContactPointsField
    v-bind="$props"
    kind="email"
    @update:model-value="emit('update:modelValue', $event)"
    @validation-change="emit('validation-change', $event)"
  />
</template>
