<script setup lang="ts">
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
defineProps<{
  options: { code: string; name: string }[];
  value: string;
  disabled?: boolean;
}>();
defineEmits<{ change: [value: string] }>();
</script>
<template>
  <Select
    :model-value="value"
    :disabled="disabled"
    @update:model-value="
      (value) => {
        if (value) $emit('change', String(value));
      }
    "
    ><SelectTrigger
      id="product-locale"
      class="w-full"
      aria-label="Язык перевода"
      ><SelectValue placeholder="Выберите язык" /></SelectTrigger
    ><SelectContent
      ><SelectGroup
        ><SelectItem v-for="item in options" :key="item.code" :value="item.code"
          >{{ item.name }} ({{ item.code }})</SelectItem
        ></SelectGroup
      ></SelectContent
    ></Select
  >
</template>
