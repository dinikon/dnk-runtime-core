<script setup lang="ts">
import type { LocaleOption } from "../model/catalog.types";
defineProps<{ locale: string; options: LocaleOption[] }>();
defineEmits<{ locale: [value: string] }>();
</script>
<template>
  <label class="flex items-center gap-2 text-sm"
    >Язык<select
      aria-label="Язык"
      class="rounded-md border bg-background px-3 py-2"
      :value="locale"
      @change="$emit('locale', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Выберите язык</option>
      <option v-for="option in options" :key="option.code" :value="option.code">
        {{ option.name }} · {{ option.code }}
      </option>
    </select></label
  >
</template>
