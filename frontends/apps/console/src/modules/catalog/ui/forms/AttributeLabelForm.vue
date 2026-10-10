<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
const props = defineProps<{
  code: string;
  label: string | null;
  existing: boolean;
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [code: string, label: string];
  dirty: [value: boolean];
}>();
const code = ref(props.code),
  label = ref(props.label ?? ""),
  dirty = ref(false);
function resetFields() {
  code.value = props.code;
  label.value = props.label ?? "";
  dirty.value = false;
  emit("dirty", false);
}
watch(() => props.reset, resetFields);
watch(
  () => props.label,
  () => {
    if (!dirty.value) resetFields();
  },
);
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
</script>
<template>
  <form class="space-y-4" @submit.prevent="$emit('submit', code, label)">
    <p
      v-if="existing && label === null"
      class="rounded-md bg-muted p-3 text-sm"
    >
      Перевод подписи отсутствует. Сохраните название для выбранной locale.
    </p>
    <label class="block space-y-2"
      ><span>Код характеристики</span
      ><input
        v-model="code"
        aria-label="Код характеристики"
        pattern="[a-z][a-z0-9_]*"
        required
        maxlength="64"
        :disabled="pending || disabled || existing"
        class="w-full rounded-md border bg-background p-2"
        @input="mark"
    /></label>
    <label class="block space-y-2"
      ><span>Название характеристики</span
      ><input
        v-model="label"
        aria-label="Название характеристики"
        required
        maxlength="255"
        :disabled="pending || disabled"
        class="w-full rounded-md border bg-background p-2"
        @input="mark"
    /></label>
    <p class="text-sm text-muted-foreground">
      Тип: enum. Значения и их переводы редактируются отдельно; код остаётся
      неизменным.
    </p>
    <div class="flex flex-wrap gap-2">
      <Button type="submit" :disabled="pending || disabled">{{
        existing ? "Сохранить подпись" : "Создать характеристику"
      }}</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="pending"
        @click="resetFields"
        >Отменить</Button
      >
    </div>
  </form>
</template>
