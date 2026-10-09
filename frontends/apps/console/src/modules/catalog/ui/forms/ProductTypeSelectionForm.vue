<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { ProductType } from "../../model/catalog.types";
const props = defineProps<{
  typeId: string;
  types: ProductType[];
  pending: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [typeId: string];
  dirty: [value: boolean];
}>();
const selected = ref(props.typeId);
watch(selected, (v) => emit("dirty", v !== props.typeId));
watch(
  () => props.reset,
  () => {
    selected.value = props.typeId;
    emit("dirty", false);
  },
);
</script>
<template>
  <form class="space-y-4" @submit.prevent="$emit('submit', selected)">
    <label class="block space-y-2"
      ><span>Новый тип контента</span
      ><select
        v-model="selected"
        aria-label="Новый тип контента"
        class="block w-full rounded-md border bg-background p-2"
        :disabled="pending"
      >
        <option v-for="type in types" :key="type.id" :value="type.id">
          {{ type.label ?? type.code }}
        </option>
      </select></label
    >
    <p class="text-sm text-muted-foreground">
      Сервер проверит контент товара и позиции во всех сохранённых языках.
      Несовместимый переход будет отклонён.
    </p>
    <div class="flex gap-2">
      <Button
        type="submit"
        :disabled="pending || !selected || selected === typeId"
        >Сменить тип</Button
      ><Button
        variant="outline"
        type="button"
        :disabled="pending"
        @click="
          selected = props.typeId;
          emit('dirty', false);
        "
        >Отменить</Button
      >
    </div>
  </form>
</template>
