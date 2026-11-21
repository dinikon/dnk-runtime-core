<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
defineProps<{ search: string; disabled: boolean }>();
const emit = defineEmits<{ change: [value: string]; submit: []; clear: [] }>();
</script>
<template>
  <form
    class="flex flex-wrap gap-2"
    role="search"
    @submit.prevent="emit('submit')"
  >
    <label for="stock-serials-search" class="sr-only"
      >Поиск по номеру экземпляра</label
    >
    <Input
      id="stock-serials-search"
      class="min-w-0 flex-1 sm:max-w-md"
      placeholder="Поиск по номеру экземпляра"
      :model-value="search"
      :disabled="disabled"
      @update:model-value="emit('change', String($event))"
    />
    <Button type="submit" variant="outline" :disabled="disabled">Найти</Button
    ><Button
      v-if="search"
      type="button"
      variant="ghost"
      :disabled="disabled"
      @click="emit('clear')"
      >Сбросить</Button
    >
  </form>
</template>
