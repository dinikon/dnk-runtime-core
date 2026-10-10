<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
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
    code: o.code,
    label: o.label ?? "",
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
  rows.value.push({ key: crypto.randomUUID(), id: null, code: "", label: "" });
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
    class="space-y-4"
    @submit.prevent="
      $emit(
        'submit',
        rows.map((r) => ({ id: r.id, code: r.code, label: r.label })),
      )
    "
  >
    <fieldset :disabled="pending || disabled" class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="font-medium">Значения enum</h2>
        <Button type="button" variant="outline" @click="add"
          >Добавить значение</Button
        >
      </div>
      <p class="text-sm text-muted-foreground">
        Порядок и подписи сохраняются одним действием. Используемое в осях
        значение удалить нельзя. Другие locale сохраняются.
      </p>
      <p v-if="!rows.length" class="rounded-md bg-muted p-3 text-sm">
        Значений пока нет.
      </p>
      <div
        v-for="(row, index) in rows"
        :key="row.key"
        class="space-y-3 rounded-md border p-3"
      >
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="space-y-1"
            ><span class="text-sm">Код значения</span
            ><input
              v-model="row.code"
              :aria-label="`Код значения ${index + 1}`"
              pattern="[a-z][a-z0-9_]*"
              required
              maxlength="64"
              :readonly="!!row.id"
              class="w-full rounded-md border bg-background p-2"
              @input="mark" /></label
          ><label class="space-y-1"
            ><span class="text-sm">Название значения</span
            ><input
              v-model="row.label"
              :aria-label="`Название значения ${index + 1}`"
              required
              maxlength="255"
              class="w-full rounded-md border bg-background p-2"
              @input="mark"
          /></label>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="index === 0"
            @click="move(index, -1)"
            >Выше</Button
          ><Button
            type="button"
            variant="outline"
            :disabled="index === rows.length - 1"
            @click="move(index, 1)"
            >Ниже</Button
          ><Button type="button" variant="ghost" @click="remove(index)"
            >Убрать значение</Button
          >
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button type="submit">Сохранить значения</Button
        ><Button type="button" variant="outline" @click="resetFields"
          >Отменить</Button
        >
      </div>
    </fieldset>
  </form>
</template>
