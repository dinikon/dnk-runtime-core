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
  inheritedTitle?: string | null;
  titleInheritance?: boolean;
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
function inherit(id: string) {
  delete values.value[id];
  dirty.value = true;
  emit("dirty", true);
}
function override(id: string) {
  change(id, props.inheritedTitle ?? "");
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
    <div v-for="block in blocks" :key="block.blockId" class="block space-y-2">
      <span
        >{{ block.label ?? block.code }}
        <span v-if="block.required" class="text-destructive">*</span></span
      >
      <div
        v-if="titleInheritance && block.code === 'title'"
        class="space-y-2 rounded-md bg-muted p-3 text-sm"
      >
        <p>
          {{
            Object.prototype.hasOwnProperty.call(values, block.blockId)
              ? "Собственное название варианта"
              : "Наследуется от товара"
          }}
          · {{ inheritedTitle ?? "Название товара в этой locale отсутствует" }}
        </p>
        <Button
          v-if="!Object.prototype.hasOwnProperty.call(values, block.blockId)"
          type="button"
          variant="outline"
          :disabled="pending || disabled"
          @click="override(block.blockId)"
          >Переопределить Title</Button
        >
        <Button
          v-else
          type="button"
          variant="outline"
          :disabled="pending || disabled"
          @click="inherit(block.blockId)"
          >Вернуть наследование</Button
        >
      </div>
      <textarea
        :value="
          values[block.blockId] ??
          (titleInheritance && block.code === 'title'
            ? (inheritedTitle ?? '')
            : '')
        "
        :aria-label="block.label ?? block.code"
        :disabled="
          disabled ||
          pending ||
          (titleInheritance &&
            block.code === 'title' &&
            !Object.prototype.hasOwnProperty.call(values, block.blockId))
        "
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
      >
    </div>
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
