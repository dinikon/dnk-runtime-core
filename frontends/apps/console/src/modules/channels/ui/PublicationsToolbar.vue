<script setup lang="ts">
import { ref, watch } from "vue";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Button } from "@/components/ui/button";
import { stockLabels } from "../model/channels.presentation";
const props = defineProps<{ search: string; stockStatus: string }>();
const emit = defineEmits<{
  change: [filters: { search: string; stockStatus: string }];
}>();
const searchInput = ref(props.search),
  stockInput = ref(props.stockStatus);
watch(
  () => props.search,
  (value) => (searchInput.value = value),
);
watch(
  () => props.stockStatus,
  (value) => (stockInput.value = value),
);
function submit(): void {
  emit("change", {
    search: searchInput.value.trim(),
    stockStatus: stockInput.value,
  });
}
</script>
<template>
  <form class="flex flex-wrap items-end gap-3" @submit.prevent="submit">
    <FieldGroup
      class="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-end"
      ><Field class="min-w-0 flex-1">
        <FieldLabel for="publication-search">Поиск публикаций</FieldLabel
        ><Input
          id="publication-search"
          v-model="searchInput"
          maxlength="200"
          placeholder="Название, SKU или внешний ID"
        />
      </Field>
      <Field class="sm:w-auto">
        <FieldLabel for="publication-stock">Наличие</FieldLabel
        ><NativeSelect id="publication-stock" v-model="stockInput"
          ><NativeSelectOption value="">Все статусы</NativeSelectOption
          ><NativeSelectOption
            v-for="(label, value) in stockLabels"
            :key="value"
            :value="value"
            >{{ label }}</NativeSelectOption
          ></NativeSelect
        >
      </Field></FieldGroup
    >
    <Button type="submit" variant="outline">Найти</Button>
  </form>
</template>
