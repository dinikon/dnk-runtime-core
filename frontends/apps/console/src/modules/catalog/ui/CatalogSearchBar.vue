<script setup lang="ts">
import { ref, watch } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
const props = defineProps<{ value: string }>();
defineEmits<{ search: [value: string] }>();
const search = ref(props.value);
watch(
  () => props.value,
  (value) => (search.value = value),
);
</script>
<template>
  <form class="flex max-w-xl gap-2" @submit.prevent="$emit('search', search)">
    <Input
      v-model="search"
      aria-label="Поиск"
      placeholder="Название, содержимое или ID…"
    /><Button variant="outline" type="submit">Найти</Button
    ><Button v-if="value" variant="ghost" @click="$emit('search', '')"
      >Сбросить</Button
    >
  </form>
</template>
