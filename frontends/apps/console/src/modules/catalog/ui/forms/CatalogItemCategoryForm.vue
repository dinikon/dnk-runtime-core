<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import type {
  CategoryOption,
  CategorySelection,
} from "../../model/category.types";
import { choosePrimary } from "../../model/category-tree";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
const props = defineProps<{
  value: CategorySelection;
  options: CategoryOption[];
  reset: number;
  disabled: boolean;
  parentId: string | null;
  locale: string;
}>();
const emit = defineEmits<{ change: [value: CategorySelection] }>();
const { value: draft, change } = useProductSectionDraft(
  () => props.value,
  () => props.reset,
  (value) => emit("change", value),
);
const labels = computed(
  () => new Map(props.options.map((option) => [option.id, option.path])),
);
const available = computed(() =>
  props.options.filter(
    (row) =>
      row.id !== draft.value.primary_category_id &&
      !draft.value.additional_category_ids.includes(row.id),
  ),
);
function add(event: Event): void {
  const input = event.target as HTMLSelectElement;
  if (input.value)
    change({
      ...draft.value,
      additional_category_ids: [
        ...draft.value.additional_category_ids,
        input.value,
      ],
    });
  input.value = "";
}
</script>
<template>
  <fieldset class="grid gap-3" :disabled="disabled">
    <label class="grid gap-1 text-sm"
      >Основная категория
      <span v-if="parentId">{{ labels.get(value.primary_category_id) }}</span>
      <NativeSelect
        v-else
        aria-label="Основная категория"
        :model-value="draft.primary_category_id"
        @update:model-value="change(choosePrimary(draft, String($event)))"
      >
        <option v-for="row in options" :key="row.id" :value="row.id">
          {{ row.path }}
        </option>
      </NativeSelect>
    </label>
    <ul
      v-if="draft.additional_category_ids.length"
      aria-label="Дополнительные категории"
      class="grid gap-2"
    >
      <li
        v-for="id in draft.additional_category_ids"
        :key="id"
        class="flex flex-wrap items-center gap-2"
      >
        <span class="text-sm">{{ labels.get(id) }}</span>
        <template v-if="!parentId">
          <Button
            variant="outline"
            size="sm"
            @click="change(choosePrimary(draft, id))"
            >Сделать основной</Button
          >
          <Button
            variant="ghost"
            size="sm"
            @click="
              change({
                ...draft,
                additional_category_ids: draft.additional_category_ids.filter(
                  (key) => key !== id,
                ),
              })
            "
            >Снять</Button
          >
        </template>
      </li>
    </ul>
    <RouterLink
      v-if="parentId"
      class="text-sm underline"
      :to="{
        path: '/catalog/items/' + parentId,
        query: { locale, tab: 'categories' },
      }"
      >Категории родительской карточки</RouterLink
    >
    <label v-else-if="available.length" class="grid gap-1 text-sm"
      >Добавить категорию
      <select
        aria-label="Добавить категорию"
        class="h-9 rounded-md border bg-background px-2"
        @change="add"
      >
        <option value="">Выберите категорию</option>
        <option v-for="row in available" :key="row.id" :value="row.id">
          {{ row.path }}
        </option>
      </select>
    </label>
  </fieldset>
</template>
