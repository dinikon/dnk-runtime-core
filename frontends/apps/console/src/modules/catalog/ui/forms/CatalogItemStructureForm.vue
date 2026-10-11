<script setup lang="ts">
import { clone } from "../../model/clone";
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { CatalogAttribute } from "../../model/catalog.types";
import type { StructureDTO } from "../../api/catalog.dto";
const props = defineProps<{
  initial: StructureDTO | null;
  attributes: CatalogAttribute[];
  pending: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [value: StructureDTO];
  dirty: [value: boolean];
}>();
const value = ref<StructureDTO>({
    axes: [],
    variants: [],
    default_selection: null,
  }),
  dirty = ref(false),
  error = ref("");
function resetFields() {
  value.value = clone(
    props.initial ?? {
      axes: [],
      variants: [
        { item_id: null, selection: [] },
        { item_id: null, selection: [] },
      ],
      default_selection: null,
    },
  );
  dirty.value = false;
  error.value = "";
  emit("dirty", false);
}
resetFields();
watch(() => props.reset, resetFields);
watch(
  () => props.initial,
  () => {
    if (!dirty.value) resetFields();
  },
);
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
function addAxis() {
  const a = props.attributes.find(
    (a) =>
      a.options.length &&
      !value.value.axes.some((x) => x.attribute_id === a.id),
  );
  if (!a) {
    error.value = "Добавьте характеристику с enum значениями.";
    return;
  }
  value.value.axes.push({
    attribute_id: a.id,
    option_ids: a.options.map((o) => o.id),
    position: value.value.axes.length,
    visible: true,
  });
  for (const v of value.value.variants)
    v.selection.push({ attribute_id: a.id, option_id: a.options[0]?.id ?? "" });
  mark();
}
function removeAxis(index: number) {
  const a = value.value.axes.splice(index, 1)[0];
  if (a)
    for (const v of value.value.variants)
      v.selection = v.selection.filter(
        (s) => s.attribute_id !== a.attribute_id,
      );
  mark();
}
function addVariant() {
  value.value.variants.push({
    item_id: null,
    selection: value.value.axes.map((a) => ({
      attribute_id: a.attribute_id,
      option_id: a.option_ids[0] ?? "",
    })),
  });
  mark();
}
function submit() {
  error.value = "";
  if (!value.value.axes.length || value.value.variants.length < 2) {
    error.value = "Нужны ось и минимум два варианта.";
    return;
  }
  const keys = value.value.variants.map((v) =>
    JSON.stringify(
      [...v.selection].sort((a, b) =>
        a.attribute_id.localeCompare(b.attribute_id),
      ),
    ),
  );
  if (new Set(keys).size !== keys.length) {
    error.value = "Комбинации вариантов должны различаться.";
    return;
  }
  emit("submit", {
    ...value.value,
    axes: value.value.axes.map((a, position) => ({ ...a, position })),
  });
}
function defaultVariant(event: Event) {
  const index = Number((event.target as HTMLSelectElement).value);
  value.value.default_selection =
    index < 0 ? null : clone(value.value.variants[index]?.selection ?? []);
  mark();
}
</script>
<template>
  <form class="space-y-4" @submit.prevent="submit">
    <fieldset :disabled="pending" class="space-y-4">
      <div class="flex flex-wrap justify-between gap-2">
        <h3 class="font-medium">Оси и варианты</h3>
        <Button type="button" variant="outline" @click="addAxis"
          >Добавить ось</Button
        >
      </div>
      <div
        v-for="(axis, index) in value.axes"
        :key="axis.attribute_id"
        class="space-y-2 rounded border p-3"
      >
        <div class="flex justify-between gap-2">
          <span>{{
            attributes.find((a) => a.id === axis.attribute_id)?.label ??
            attributes.find((a) => a.id === axis.attribute_id)?.code
          }}</span
          ><Button type="button" variant="ghost" @click="removeAxis(index)"
            >Убрать ось</Button
          >
        </div>
        <label
          ><input v-model="axis.visible" type="checkbox" @change="mark" />
          Показывать характеристику</label
        >
        <div class="flex flex-wrap gap-3">
          <label
            v-for="o in attributes.find((a) => a.id === axis.attribute_id)
              ?.options ?? []"
            :key="o.id"
            ><input
              v-model="axis.option_ids"
              type="checkbox"
              :value="o.id"
              @change="mark"
            />
            {{ o.label ?? o.code }}</label
          >
        </div>
      </div>
      <div
        v-for="(variant, index) in value.variants"
        :key="variant.item_id ?? index"
        class="flex flex-wrap items-end gap-3 rounded border p-3"
      >
        <span>Вариант {{ index + 1 }}</span
        ><label
          v-for="s in variant.selection"
          :key="s.attribute_id"
          class="min-w-32"
          ><span class="block text-sm">{{
            attributes.find((a) => a.id === s.attribute_id)?.label ??
            attributes.find((a) => a.id === s.attribute_id)?.code
          }}</span
          ><select
            v-model="s.option_id"
            class="w-full rounded border bg-background p-2"
            @change="mark"
          >
            <option
              v-for="o in attributes
                .find((a) => a.id === s.attribute_id)
                ?.options.filter((o) =>
                  value.axes
                    .find((a) => a.attribute_id === s.attribute_id)
                    ?.option_ids.includes(o.id),
                ) ?? []"
              :key="o.id"
              :value="o.id"
            >
              {{ o.label ?? o.code }}
            </option>
          </select></label
        ><Button
          type="button"
          variant="ghost"
          @click="
            value.variants.splice(index, 1);
            mark();
          "
          >Удалить вариант</Button
        >
      </div>
      <Button type="button" variant="outline" @click="addVariant"
        >Добавить вариант</Button
      ><label class="block space-y-1"
        ><span>Вариант по умолчанию</span
        ><select
          class="w-full rounded border bg-background p-2"
          @change="defaultVariant"
        >
          <option value="-1" :selected="!value.default_selection">
            Не выбран
          </option>
          <option
            v-for="(v, index) in value.variants"
            :key="index"
            :value="index"
            :selected="
              JSON.stringify(v.selection) ===
              JSON.stringify(value.default_selection)
            "
          >
            Вариант {{ index + 1 }}
          </option>
        </select></label
      >
      <p v-if="error" role="alert">{{ error }}</p>
      <div class="flex gap-2">
        <Button type="submit">Сохранить структуру</Button
        ><Button type="button" variant="outline" @click="resetFields"
          >Отмена</Button
        >
      </div>
    </fieldset>
  </form>
</template>
