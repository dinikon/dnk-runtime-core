<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
const props = defineProps<{
  label: string | null;
  existing: boolean;
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [label: string];
  dirty: [value: boolean];
}>();
const label = ref(props.label ?? ""),
  dirty = ref(false);
function resetFields() {
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
  <form class="flex flex-col gap-4" @submit.prevent="$emit('submit', label)">
    <FieldGroup>
      <Field :data-disabled="pending || disabled">
        <FieldLabel for="attribute-label">Название характеристики</FieldLabel>
        <Input
          id="attribute-label"
          v-model="label"
          required
          maxlength="255"
          :disabled="pending || disabled"
          @input="mark"
        />
        <FieldDescription v-if="existing && props.label === null">
          Нет перевода. Сохраните название для выбранного языка.
        </FieldDescription>
        <FieldDescription>
          Значения характеристики и их переводы редактируются отдельно.
        </FieldDescription>
      </Field>
    </FieldGroup>
    <div class="flex flex-wrap gap-2">
      <Button type="submit" :disabled="pending || disabled">{{
        existing ? "Сохранить подпись" : "Создать характеристику"
      }}</Button>
      <Button
        type="button"
        variant="outline"
        :disabled="pending"
        @click="resetFields"
        >Отменить</Button
      >
    </div>
  </form>
</template>
