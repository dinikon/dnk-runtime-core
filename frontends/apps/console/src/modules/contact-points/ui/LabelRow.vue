<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { Badge } from "@/components/ui/badge";
import type { ContactPointLabel } from "../model/types";
const props = defineProps<{ label: ContactPointLabel; pending: boolean }>();
const emit = defineEmits<{
  save: [id: string, name: string];
  toggle: [label: ContactPointLabel];
}>();
const name = ref(props.label.name),
  attempted = ref(false);
watch(
  () => props.label.name,
  (value) => {
    name.value = value;
    attempted.value = false;
  },
);
function save() {
  attempted.value = true;
  if (!name.value.trim() || name.value.trim().length > 100 || props.pending)
    return;
  emit("save", props.label.id, name.value.trim());
}
</script>
<template>
  <form
    class="flex flex-wrap items-start gap-2"
    @submit.prevent="save"
    novalidate
  >
    <Field
      class="min-w-48 flex-1"
      :data-invalid="(attempted && !name.trim()) || undefined"
    >
      <FieldLabel :for="`label-${label.id}`" class="sr-only"
        >Подпись {{ label.name }}</FieldLabel
      >
      <Input
        :id="`label-${label.id}`"
        v-model="name"
        maxlength="100"
        :disabled="pending"
        :aria-invalid="attempted && !name.trim()"
      />
      <FieldError v-if="attempted && !name.trim()"
        >Введите название подписи.</FieldError
      >
    </Field>
    <Badge v-if="!label.isActive" variant="secondary" class="self-center"
      >Архив</Badge
    >
    <Button
      type="submit"
      variant="outline"
      :disabled="pending || name.trim() === label.name"
      >Сохранить</Button
    >
    <Button
      type="button"
      variant="ghost"
      :disabled="pending"
      @click="emit('toggle', label)"
      >{{ label.isActive ? "Архивировать" : "Восстановить" }}</Button
    >
  </form>
</template>
