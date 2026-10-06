<script setup lang="ts">
import { computed } from "vue";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { ProductTypeBlockDto, ContentScope } from "../api/contracts";
import RichTextEditor from "./RichTextEditor.vue";

const props = defineProps<{
  blocks: ProductTypeBlockDto[];
  scope: ContentScope;
  modelValue: Record<string, string>;
  labelLocale?: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: Record<string, string>] }>();
const fields = computed(() => props.blocks.filter((block) => block.scope === props.scope).sort((a, b) => a.position - b.position));
function label(block: ProductTypeBlockDto) {
  const language = props.labelLocale?.split("-")[0] ?? "";
  return block.translations[props.labelLocale ?? ""] ?? block.translations[language] ?? block.translations.en ?? block.code;
}
function setValue(code: string, value: string) {
  emit("update:modelValue", { ...props.modelValue, [code]: value });
}
</script>
<template>
  <div class="grid gap-4">
    <p v-if="!fields.length" class="text-sm text-muted-foreground">У этого типа нет блоков для выбранной области.</p>
    <Field v-for="block in fields" :key="`${scope}:${block.block_id}`">
      <FieldLabel :for="`content-${scope}-${block.block_id}`">{{ label(block) }} <span v-if="block.required" aria-label="Обязательное поле">*</span></FieldLabel>
      <Input v-if="block.type === 'text'" :id="`content-${scope}-${block.block_id}`" :model-value="modelValue[block.code] ?? ''" :disabled="disabled" :maxlength="block.code === 'title' ? 255 : 4096" @update:model-value="setValue(block.code, String($event))" />
      <RichTextEditor v-else :model-value="modelValue[block.code] ?? ''" :disabled="disabled" @update:model-value="setValue(block.code, $event)" />
      <p class="text-xs text-muted-foreground">{{ block.code }}</p>
    </Field>
  </div>
</template>
