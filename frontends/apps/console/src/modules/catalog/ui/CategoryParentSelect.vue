<script setup lang="ts">
import { computed } from "vue";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { categoryLabel, descendants } from "../model/categories";
import type { CategoryListDto } from "../api/contracts";
const props = defineProps<{
  items: CategoryListDto[];
  excludeId?: string;
  disabled?: boolean;
}>();
const value = defineModel<string | null>({ required: true });
const options = computed(() => {
  const excluded = props.excludeId
    ? descendants(props.items, props.excludeId)
    : new Set();
  return props.items
    .filter((item) => !excluded.has(item.id))
    .sort((a, b) => categoryLabel(a).localeCompare(categoryLabel(b)));
});
const label = (item: CategoryListDto) => {
  const parts = [categoryLabel(item)];
  const seen = new Set([item.id]);
  let parent = item.parent_id;
  while (parent && !seen.has(parent)) {
    seen.add(parent);
    const next = props.items.find((candidate) => candidate.id === parent);
    if (!next) break;
    parts.unshift(categoryLabel(next));
    parent = next.parent_id;
  }
  return parts.join(" / ");
};
const selectedLabel = computed(() => {
  if (!value.value) return "Без родителя";
  const item = props.items.find((item) => item.id === value.value);
  return item ? label(item) : value.value;
});
</script>
<template>
  <Select
    :model-value="value ?? '__root__'"
    :disabled="disabled"
    @update:model-value="
      (next) => {
        if (next) value = String(next) === '__root__' ? null : String(next);
      }
    "
    ><SelectTrigger
      id="category-parent"
      class="w-full"
      aria-label="Родительская категория"
      ><SelectValue>{{ selectedLabel }}</SelectValue></SelectTrigger
    ><SelectContent
      ><SelectGroup
        ><SelectItem value="__root__">Без родителя</SelectItem
        ><SelectItem v-for="item in options" :key="item.id" :value="item.id">{{
          label(item)
        }}</SelectItem></SelectGroup
      ></SelectContent
    ></Select
  >
</template>
