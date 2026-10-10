<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
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
</script>
<template>
  <form class="space-y-4" @submit.prevent="emit('submit', label)">
    <p v-if="existing && props.label === null" class="text-sm text-muted-foreground">
      Перевод отсутствует. Введите название для выбранной locale.
    </p>
    <label class="block space-y-2"
      ><span>Название</span
      ><input
        v-model="label"
        aria-label="Название"
        required
        maxlength="255"
        :disabled="pending || disabled"
        class="w-full rounded-md border bg-background p-2"
        @input="
          dirty = true;
          emit('dirty', true);
        "
    /></label>
    <div class="flex flex-wrap gap-2">
      <Button type="submit" :disabled="pending || disabled">{{
        existing ? "Сохранить название" : "Создать"
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
