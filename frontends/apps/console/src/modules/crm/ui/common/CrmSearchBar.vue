<script setup lang="ts">
import { Search } from "@lucide/vue";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";

defineProps<{ modelValue: string; placeholder: string }>();
defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <InputGroup class="max-w-xl">
    <InputGroupAddon><Search /></InputGroupAddon>
    <InputGroupInput
      :model-value="modelValue"
      :placeholder="placeholder"
      aria-label="Поиск"
      @update:model-value="$emit('update:modelValue', String($event))"
    />
  </InputGroup>
</template>
