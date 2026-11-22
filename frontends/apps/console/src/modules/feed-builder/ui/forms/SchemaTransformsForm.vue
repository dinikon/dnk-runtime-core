<script setup lang="ts">
import { ref } from "vue";
import { ArrowUp, ArrowDown, Trash2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import {
  Field,
  FieldGroup,
  FieldSet,
  FieldLegend,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import type {
  DraftTransform,
  FieldKind,
  SchemaMetadata,
} from "../../model/feed-schema.types";
const props = defineProps<{
  value: DraftTransform[];
  kind: FieldKind;
  metadata: SchemaMetadata;
  disabled: boolean;
}>();
const emit = defineEmits<{ change: [value: DraftTransform[]] }>();
const choice = ref("");
function add(value: string): void {
  const selected = props.metadata.transforms.find(
    (t) => t.operation === value && t.fieldKinds.includes(props.kind),
  );
  if (
    !selected ||
    props.disabled ||
    props.value.length >= props.metadata.maxTransforms
  )
    return;
  emit("change", [
    ...props.value,
    {
      operation: selected.operation,
      parameter:
        selected.parameterKind === "step"
          ? "1"
          : selected.parameterKind === "max_length"
            ? "255"
            : "",
    },
  ]);
  choice.value = "";
}
function parameter(index: number, value: string): void {
  emit(
    "change",
    props.value.map((t, i) =>
      i === index ? { ...t, parameter: value } : { ...t },
    ),
  );
}
function move(index: number, delta: number): void {
  const result = [...props.value],
    next = index + delta;
  if (next < 0 || next >= result.length) return;
  const [item] = result.splice(index, 1);
  result.splice(next, 0, item!);
  emit("change", result);
}
</script>
<template>
  <FieldSet :disabled="disabled">
    <FieldLegend>Преобразования</FieldLegend>
    <FieldDescription
      >Настройки применяются в указанном порядке при обработке
      значения.</FieldDescription
    >
    <FieldGroup>
      <Field v-for="(item, index) in value" :key="index">
        <FieldLabel :for="`transform-${index}`">{{
          metadata.transforms.find((t) => t.operation === item.operation)
            ?.label ?? item.operation
        }}</FieldLabel>
        <Input
          v-if="item.operation !== 'string.trim'"
          :id="`transform-${index}`"
          :model-value="item.parameter"
          :inputmode="
            item.operation === 'string.truncate' ? 'numeric' : 'decimal'
          "
          :aria-label="
            item.operation === 'string.truncate'
              ? 'Длина обрезания'
              : 'Шаг округления'
          "
          @update:model-value="parameter(index, String($event))"
        />
        <div class="flex gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled || index === 0"
            aria-label="Поднять преобразование"
            @click="move(index, -1)"
            ><ArrowUp /></Button
          ><Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled || index === value.length - 1"
            aria-label="Опустить преобразование"
            @click="move(index, 1)"
            ><ArrowDown /></Button
          ><Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled"
            aria-label="Удалить преобразование"
            @click="
              emit(
                'change',
                value.filter((_, i) => i !== index),
              )
            "
            ><Trash2
          /></Button>
        </div>
      </Field>
      <Field v-if="!disabled">
        <FieldLabel for="add-schema-transform"
          >Добавить преобразование</FieldLabel
        >
        <Select
          :model-value="choice"
          :disabled="value.length >= metadata.maxTransforms"
          @update:model-value="add(String($event))"
          ><SelectTrigger id="add-schema-transform"
            ><SelectValue
              placeholder="Выберите преобразование" /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="t in metadata.transforms.filter((t) =>
                  t.fieldKinds.includes(kind),
                )"
                :key="t.operation"
                :value="t.operation"
                >{{ t.label }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        >
      </Field>
    </FieldGroup>
  </FieldSet>
</template>
