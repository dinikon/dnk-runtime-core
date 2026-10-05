<script setup lang="ts">
import { computed } from "vue";
import { categoryTree } from "../model/categories";
import type { CategoryListDto } from "../api/contracts";
import CategoryTreeNode from "./CategoryTreeNode.vue";
const props = defineProps<{
  items: CategoryListDto[];
  locale: string;
  selectable?: boolean;
  selected?: string[];
  disabled?: boolean;
}>();
const nodes = computed(() => categoryTree(props.items));
defineEmits<{ toggle: [id: string] }>();
</script>
<template>
  <ul class="flex flex-col gap-2" aria-label="Дерево категорий">
    <CategoryTreeNode
      v-for="node in nodes"
      :key="node.id"
      :node="node"
      :locale="locale"
      :depth="0"
      :selectable="selectable"
      :selected="selected"
      :disabled="disabled"
      @toggle="$emit('toggle', $event)"
    />
  </ul>
</template>
