<script setup lang="ts">
import { Search } from "@lucide/vue";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";

defineProps<{ modelValue: string }>();
const emit = defineEmits<{
  "update:modelValue": [value: string];
  submit: [];
}>();
</script>

<template>
  <form role="search" class="min-w-0" @submit.prevent="emit('submit')">
    <InputGroup>
      <InputGroupInput
        :model-value="modelValue"
        type="search"
        aria-label="Search"
        placeholder="Search"
        @update:model-value="emit('update:modelValue', String($event))"
      />
      <InputGroupAddon><Search aria-hidden="true" /></InputGroupAddon>
    </InputGroup>
  </form>
</template>
