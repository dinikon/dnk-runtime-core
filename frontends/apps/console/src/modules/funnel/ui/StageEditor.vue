<script setup lang="ts">
import { ref, useId } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import type { FunnelStageDraft } from "../model/funnel.types";
const props = defineProps<{
  modelValue: FunnelStageDraft[];
  disabled?: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: FunnelStageDraft[]];
}>();
const dragged = ref<number | null>(null),
  uid = useId();
function change(index: number, key: "name" | "color", value: string) {
  emit(
    "update:modelValue",
    props.modelValue.map((s, i) => (i === index ? { ...s, [key]: value } : s)),
  );
}
function move(from: number, to: number) {
  if (to < 0 || to >= props.modelValue.length || props.disabled) return;
  const value = [...props.modelValue],
    item = value.splice(from, 1)[0]!;
  value.splice(to, 0, item);
  emit("update:modelValue", value);
}
function remove(index: number) {
  if (props.modelValue[index]?.id || props.modelValue.length === 1) return;
  emit(
    "update:modelValue",
    props.modelValue.filter((_, i) => i !== index),
  );
}
function add() {
  emit("update:modelValue", [
    ...props.modelValue,
    { clientKey: crypto.randomUUID(), name: "Новая стадия", color: "neutral" },
  ]);
}
</script>
<template>
  <div class="flex flex-col gap-4">
    <article
      v-for="(stage, index) in modelValue"
      :key="stage.id ?? stage.clientKey"
      class="flex flex-col gap-3 rounded-lg border p-4"
      @dragover.prevent
      @drop.prevent="
        dragged !== null && move(dragged, index);
        dragged = null;
      "
    >
      <div class="flex items-center justify-between gap-2">
        <p class="text-sm font-medium">
          Стадия {{ index + 1 }}
          <span v-if="index === 0" class="text-muted-foreground"
            >· начальная для новых назначений</span
          >
        </p>
        <div class="flex gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="disabled || index === 0"
            :aria-label="'Поднять стадию ' + stage.name"
            @click="move(index, index - 1)"
            >↑</Button
          ><Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="disabled || index === modelValue.length - 1"
            :aria-label="'Опустить стадию ' + stage.name"
            @click="move(index, index + 1)"
            >↓</Button
          ><Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="disabled || !!stage.id || modelValue.length === 1"
            :title="
              stage.id ? 'Удаление сохранённых стадий пока недоступно' : ''
            "
            @click="remove(index)"
            >Удалить</Button
          ><button
            type="button"
            draggable="true"
            :disabled="disabled"
            :aria-label="'Перетащить стадию ' + stage.name"
            class="cursor-grab rounded px-2"
            @dragstart="
              dragged = index;
              $event.dataTransfer?.setData('text/plain', String(index));
            "
            @dragend="dragged = null"
          >
            ⠿
          </button>
        </div>
      </div>
      <FieldGroup
        ><Field
          ><FieldLabel :for="uid + index + 'name'">Название *</FieldLabel
          ><Input
            :id="uid + index + 'name'"
            :model-value="stage.name"
            required
            maxlength="100"
            :disabled="disabled"
            @update:model-value="
              change(index, 'name', String($event))
            " /></Field
        ><Field
          ><FieldLabel :for="uid + index + 'color'">Цвет</FieldLabel
          ><NativeSelect
            :id="uid + index + 'color'"
            :model-value="stage.color"
            :disabled="disabled"
            @update:model-value="change(index, 'color', String($event))"
            ><option value="neutral">Нейтральный</option>
            <option value="blue">Синий</option>
            <option value="green">Зелёный</option>
            <option value="amber">Янтарный</option>
            <option value="red">Красный</option>
            <option value="violet">Фиолетовый</option></NativeSelect
          ></Field
        ></FieldGroup
      >
    </article>
    <Button
      type="button"
      variant="outline"
      :disabled="disabled || modelValue.length >= 50"
      @click="add"
      >Добавить стадию</Button
    >
    <p class="text-sm text-muted-foreground">
      Переименование и перестановка сохраняют положение существующих карточек.
      Первая стадия применяется к новым назначениям.
    </p>
  </div>
</template>
