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
import type {
  AttributeOptionDraft,
  CatalogAttributeOption,
} from "../../model/catalog.types";
const props = defineProps<{
  options: CatalogAttributeOption[];
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [options: AttributeOptionDraft[]];
  dirty: [value: boolean];
}>();
const rows = ref<(AttributeOptionDraft & { key: string })[]>([]),
  dirty = ref(false);
function resetFields() {
  rows.value = props.options.map((o) => ({
    key: o.id,
    id: o.id,
    label: o.label,
  }));
  dirty.value = false;
  emit("dirty", false);
}
resetFields();
watch(() => props.reset, resetFields);
watch(
  () => props.options,
  () => {
    if (!dirty.value) resetFields();
  },
);
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
function add() {
  rows.value.push({ key: crypto.randomUUID(), id: null, label: "" });
  mark();
}
function remove(index: number) {
  rows.value.splice(index, 1);
  mark();
}
function move(index: number, delta: number) {
  const row = rows.value[index];
  if (!row) return;
  rows.value.splice(index, 1);
  rows.value.splice(index + delta, 0, row);
  mark();
}
</script>
<template>
  <form
    class="flex flex-col gap-4"
    @submit.prevent="
      $emit(
        'submit',
        rows.map((r) => ({ id: r.id, label: r.label })),
      )
    "
  >
    <fieldset :disabled="pending || disabled" class="flex flex-col gap-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="font-medium">Значения характеристики</h2>
        <Button type="button" variant="outline" @click="add"
          >Добавить значение</Button
        >
      </div>
      <p class="text-sm text-muted-foreground">
        Порядок и названия сохраняются одним действием. Используемое товарами
        значение удалить нельзя. Переводы на другие языки сохраняются.
      </p>
      <p v-if="!rows.length" class="text-sm text-muted-foreground">
        Значений пока нет.
      </p>
      <div
        v-for="(row, index) in rows"
        :key="row.key"
        class="flex flex-col gap-3 rounded-md border p-3"
      >
        <FieldGroup>
          <Field :data-disabled="pending || disabled">
            <FieldLabel :for="`option-label-${row.key}`"
              >Название значения</FieldLabel
            >
            <Input
              :id="`option-label-${row.key}`"
              :model-value="row.label ?? ''"
              :aria-label="`Название значения ${index + 1}`"
              :placeholder="
                row.id && row.label === null ? 'Нет перевода' : undefined
              "
              :required="!row.id || row.label !== null"
              maxlength="255"
              @update:model-value="
                row.label = String($event);
                mark();
              "
            />
            <FieldDescription v-if="row.id && row.label === null">
              Нет перевода. Можно изменить порядок или добавить название для
              выбранного языка.
            </FieldDescription>
          </Field>
        </FieldGroup>
        <div class="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="index === 0"
            @click="move(index, -1)"
            >Выше</Button
          >
          <Button
            type="button"
            variant="outline"
            :disabled="index === rows.length - 1"
            @click="move(index, 1)"
            >Ниже</Button
          >
          <Button type="button" variant="ghost" @click="remove(index)"
            >Убрать значение</Button
          >
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button type="submit">Сохранить значения</Button>
        <Button type="button" variant="outline" @click="resetFields"
          >Отменить</Button
        >
      </div>
    </fieldset>
  </form>
</template>
