<script setup lang="ts">
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type { CurrencyInfo } from "../model/types";

defineProps<{
  modelValue: string;
  currencies: CurrencyInfo[];
  id: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <NativeSelect
    :id="id"
    :model-value="modelValue"
    :disabled="disabled"
    class="w-full"
    @update:model-value="emit('update:modelValue', String($event))"
  >
    <NativeSelectOption
      v-for="currency in currencies"
      :key="currency.code"
      :value="currency.code"
      >{{ currency.code }} · {{ currency.name }}</NativeSelectOption
    >
  </NativeSelect>
</template>
