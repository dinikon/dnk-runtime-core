<script setup lang="ts">
import type { LocaleOption, ProductType } from "../model/catalog.types";
defineProps<{
  locale: string;
  options: LocaleOption[];
  types?: ProductType[];
  typeId?: string;
}>();
defineEmits<{ locale: [value: string]; type: [value: string] }>();
</script>
<template>
  <div class="flex flex-wrap gap-4">
    <label class="flex items-center gap-2 text-sm"
      >Язык<select
        class="rounded-md border bg-background px-3 py-2"
        :value="locale"
        @change="$emit('locale', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">Выберите locale</option>
        <option
          v-for="option in options"
          :key="option.code"
          :value="option.code"
        >
          {{ option.name }} · {{ option.code }}
        </option>
      </select></label
    ><label v-if="types" class="flex items-center gap-2 text-sm"
      >Тип контента<select
        class="rounded-md border bg-background px-3 py-2"
        :value="typeId ?? ''"
        @change="$emit('type', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">Все типы</option>
        <option v-for="type in types" :key="type.id" :value="type.id">
          {{ type.label ?? type.code }}
        </option>
      </select></label
    >
  </div>
</template>
