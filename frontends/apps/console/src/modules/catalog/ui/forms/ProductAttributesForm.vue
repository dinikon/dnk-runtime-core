<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type {
  CatalogAttribute,
  ProductAttributeValue,
} from "../../model/catalog.types";
const props = defineProps<{
  values: ProductAttributeValue[];
  attributes: CatalogAttribute[];
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [values: ProductAttributeValue[]];
  dirty: [value: boolean];
}>();
const rows = ref(props.values.map((v) => ({ ...v }))),
  dirty = ref(false);
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
function resetFields() {
  rows.value = props.values.map((v) => ({ ...v }));
  dirty.value = false;
  emit("dirty", false);
}
watch(() => props.reset, resetFields);
watch(
  () => props.values,
  () => {
    if (!dirty.value) resetFields();
  },
);
function options(id: string) {
  return props.attributes.find((a) => a.id === id)?.options ?? [];
}
function add() {
  rows.value.push({
    attributeId: "",
    optionId: "",
    visible: true,
    position: rows.value.length,
  });
  mark();
}
function move(index: number, delta: number) {
  const row = rows.value.splice(index, 1)[0]!;
  rows.value.splice(index + delta, 0, row);
  mark();
}
</script>
<template>
  <form
    class="space-y-4"
    @submit.prevent="
      emit(
        'submit',
        rows.map((v, position) => ({ ...v, position })),
      )
    "
  >
    <p class="text-sm text-muted-foreground">
      Общие значения описывают товар. Их изменение не меняет оси, комбинации или
      выбор по умолчанию.
    </p>
    <p v-if="!rows.length">Общие характеристики не назначены.</p>
    <fieldset
      v-for="(row, index) in rows"
      :key="index"
      class="space-y-3 rounded-md border p-3"
      :disabled="pending || disabled"
    >
      <legend class="px-1 text-sm">Характеристика {{ index + 1 }}</legend>
      <label class="block space-y-1"
        ><span>Определение</span
        ><select
          v-model="row.attributeId"
          :aria-label="`Определение ${index + 1}`"
          required
          class="w-full rounded-md border bg-background p-2"
          @change="
            row.optionId = '';
            mark();
          "
        >
          <option value="" disabled>Выберите характеристику</option>
          <option
            v-for="a in attributes.filter(
              (a) =>
                a.id === row.attributeId ||
                !rows.some((v) => v.attributeId === a.id),
            )"
            :key="a.id"
            :value="a.id"
          >
            {{ a.label ?? a.code }}
          </option>
        </select></label
      >
      <label class="block space-y-1"
        ><span>Значение</span
        ><select
          v-model="row.optionId"
          :aria-label="`Значение ${index + 1}`"
          required
          class="w-full rounded-md border bg-background p-2"
          @change="mark"
        >
          <option value="" disabled>Выберите значение</option>
          <option
            v-for="o in options(row.attributeId)"
            :key="o.id"
            :value="o.id"
          >
            {{ o.label ?? o.code }}
          </option>
        </select></label
      >
      <label class="flex items-center gap-2"
        ><input
          v-model="row.visible"
          type="checkbox"
          :aria-label="`Показывать ${index + 1}`"
          @change="mark"
        />Показывать характеристику</label
      >
      <div class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="index === 0"
          :aria-label="`Выше ${index + 1}`"
          @click="move(index, -1)"
          >Выше</Button
        ><Button
          type="button"
          variant="outline"
          :disabled="index === rows.length - 1"
          :aria-label="`Ниже ${index + 1}`"
          @click="move(index, 1)"
          >Ниже</Button
        ><Button
          type="button"
          variant="ghost"
          :aria-label="`Удалить характеристику ${index + 1}`"
          @click="
            rows.splice(index, 1);
            mark();
          "
          >Удалить</Button
        >
      </div>
    </fieldset>
    <div class="flex flex-wrap gap-2">
      <Button
        type="button"
        variant="outline"
        :disabled="pending || disabled"
        @click="add"
        >Добавить характеристику</Button
      ><Button :disabled="pending || disabled">Сохранить характеристики</Button
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
