<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
const props = defineProps<{
  virtual: boolean;
  pending: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [value: boolean];
  dirty: [value: boolean];
}>();
const value = ref(props.virtual);
watch(value, (v) => emit("dirty", v !== props.virtual));
watch(
  () => props.reset,
  () => {
    value.value = props.virtual;
    emit("dirty", false);
  },
);
</script>
<template>
  <form class="space-y-4" @submit.prevent="$emit('submit', value)">
    <label class="flex gap-2"
      ><input v-model="value" type="checkbox" :disabled="pending" />Виртуальная
      позиция</label
    >
    <p class="text-sm text-muted-foreground">
      {{
        value
          ? "Доставка не требуется. Складская связь запрещена."
          : "SKU не подключена. Габариты и масса неизвестны."
      }}
    </p>
    <p class="text-sm text-muted-foreground">
      Загрузка файла недоступна до подключения файлового сервиса.
    </p>
    <div class="flex gap-2">
      <Button type="submit" :disabled="pending">Сохранить свойства</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="pending"
        @click="
          value = props.virtual;
          emit('dirty', false);
        "
        >Отменить</Button
      >
    </div>
  </form>
</template>
