<script setup lang="ts">
import { ref, watch, useId } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
const props = defineProps<{ value: string }>();
defineEmits<{ search: [value: string] }>();
const search = ref(props.value);
const id = useId();
watch(
  () => props.value,
  (value) => (search.value = value),
);
</script>
<template>
  <form
    role="search"
    class="flex w-full min-w-0 items-center gap-2 sm:max-w-md"
    @submit.prevent="$emit('search', search)"
  >
    <FieldGroup class="min-w-0 flex-1"
      ><Field
        ><FieldLabel :for="id" class="sr-only">Поиск товаров</FieldLabel
        ><Input
          :id="id"
          v-model="search"
          placeholder="Название или SKU…" /></Field></FieldGroup
    ><Button variant="outline" type="submit">Найти</Button
    ><Button
      v-if="value"
      type="button"
      variant="ghost"
      @click="$emit('search', '')"
      >Сбросить</Button
    >
  </form>
</template>
