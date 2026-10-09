<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { SchemaBlock } from "../../model/catalog.types";
const props = defineProps<{
  blocks: SchemaBlock[];
  content: Record<string, string> | null;
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [values: Record<string, string>];
  delete: [];
  dirty: [value: boolean];
}>();
const values = ref({ ...props.content }),
  dirty = ref(false),
  errors = ref<Record<string, string>>({});
function resetFields() {
  values.value = { ...props.content };
  dirty.value = false;
  errors.value = {};
  emit("dirty", false);
}
watch(() => props.reset, resetFields);
watch(
  () => props.content,
  () => {
    if (!dirty.value) resetFields();
  },
);
function change(id: string, value: string) {
  values.value[id] = value;
  dirty.value = true;
  emit("dirty", true);
}
function submit() {
  errors.value = {};
  for (const b of props.blocks) {
    if (
      b.required &&
      !(values.value[b.blockId] ?? "").replace(/<[^>]*>/g, "").trim()
    )
      errors.value[b.blockId] = "Обязательное поле";
  }
  if (!Object.keys(errors.value).length) emit("submit", { ...values.value });
}
</script>
<template>
  <form class="space-y-4" @submit.prevent="submit">
    <p v-if="content === null" class="rounded-md bg-muted p-3 text-sm">
      Перевод отсутствует. Сохраните форму, чтобы создать его.
    </p>
    <p v-if="!blocks.length" class="text-sm text-muted-foreground">
      В этой области нет блоков. Можно сохранить пустой перевод.
    </p>
    <label v-for="block in blocks" :key="block.blockId" class="block space-y-2"
      ><span
        >{{ block.label ?? block.code }}
        <span v-if="block.required" class="text-destructive">*</span></span
      ><textarea
        :value="values[block.blockId] ?? ''"
        :aria-label="block.label ?? block.code"
        :disabled="disabled || pending"
        :rows="block.valueType === 'rich_text' ? 6 : 2"
        class="block w-full rounded-md border bg-background px-3 py-2 text-sm"
        @input="
          change(block.blockId, ($event.target as HTMLTextAreaElement).value)
        "
      /><span
        v-if="block.valueType === 'rich_text'"
        class="text-xs text-muted-foreground"
        >HTML очищается при сохранении. Форма показывает сохранённый
        результат.</span
      ><span
        v-if="errors[block.blockId]"
        class="block text-sm text-destructive"
        >{{ errors[block.blockId] }}</span
      ></label
    >
    <div class="flex flex-wrap gap-2">
      <Button type="submit" :disabled="pending || disabled"
        >Сохранить перевод</Button
      ><Button
        variant="outline"
        type="button"
        :disabled="pending"
        @click="resetFields"
        >Отменить</Button
      ><Button
        v-if="content !== null"
        variant="ghost"
        type="button"
        :disabled="pending"
        @click="$emit('delete')"
        >Удалить перевод</Button
      >
    </div>
  </form>
</template>
