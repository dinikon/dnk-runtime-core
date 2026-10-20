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
const props = defineProps<{
  search: string;
  stockStatus: string;
  bindingStatus?: string;
  identityStatus?: string;
  identityLabel?: string;
  identityKey?: string;
}>();
const emit = defineEmits<{
  change: [
    filters: {
      search: string;
      stockStatus: string;
      bindingStatus?: string;
      identityStatus?: string;
    },
  ];
}>();
const identityInput = ref(props.identityStatus ?? "");
watch(
  () => props.identityStatus,
  (value) => (identityInput.value = value ?? ""),
);
const bindingInput = ref(props.bindingStatus ?? "");
watch(
  () => props.bindingStatus,
  (value) => (bindingInput.value = value ?? ""),
);
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
    bindingStatus: bindingInput.value,
    identityStatus: identityInput.value,
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
        > </Field
      ><Field class="sm:w-auto"
        ><FieldLabel for="publication-binding">Связь с каталогом</FieldLabel
        ><NativeSelect id="publication-binding" v-model="bindingInput"
          ><NativeSelectOption value="">Все публикации</NativeSelectOption
          ><NativeSelectOption value="bound">Связанные</NativeSelectOption
          ><NativeSelectOption value="unbound"
            >Не связанные</NativeSelectOption
          ></NativeSelect
        ></Field
      ></FieldGroup
    >
    <Field v-if="identityLabel" class="w-full sm:w-auto">
      <FieldLabel for="publication-identity">{{ identityLabel }}</FieldLabel>
      <NativeSelect id="publication-identity" v-model="identityInput">
        <NativeSelectOption value="">Все ключи</NativeSelectOption>
        <NativeSelectOption value="missing">Без ключа</NativeSelectOption>
        <NativeSelectOption value="duplicate"
          >Дублирующийся ключ</NativeSelectOption
        >
        <NativeSelectOption value="valid">Ключ указан</NativeSelectOption>
      </NativeSelect>
    </Field>
    <p
      v-if="identityKey"
      class="max-w-full break-all text-xs text-muted-foreground"
    >
      Ключ: {{ identityKey }}
    </p>
    <Button type="submit" variant="outline">Найти</Button>
  </form>
</template>
