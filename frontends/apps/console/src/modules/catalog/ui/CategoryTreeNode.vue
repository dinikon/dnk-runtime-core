<script setup lang="ts">
import { ref } from "vue";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight } from "@lucide/vue";
import { categoryLabel, type CategoryNode } from "../model/categories";
const props = defineProps<{
  node: CategoryNode;
  locale: string;
  depth: number;
  selectable?: boolean;
  selected?: string[];
  disabled?: boolean;
}>();
defineEmits<{ toggle: [id: string] }>();
const open = ref(props.depth === 0);
</script>
<template>
  <li class="min-w-0">
    <div class="flex min-w-0 items-center gap-2">
      <Button
        v-if="node.children.length"
        type="button"
        variant="ghost"
        size="icon"
        :aria-expanded="open"
        :aria-label="`${open ? 'Свернуть' : 'Раскрыть'} ${categoryLabel(node)}`"
        @click="open = !open"
        ><ChevronDown v-if="open" /><ChevronRight v-else /></Button
      ><span v-else class="size-8 shrink-0" /><label
        v-if="selectable"
        class="flex min-w-0 items-center gap-2 text-sm"
        ><input
          type="checkbox"
          :checked="selected?.includes(node.id)"
          :disabled="disabled"
          @change="$emit('toggle', node.id)"
        /><span class="break-words">{{ categoryLabel(node) }}</span></label
      ><RouterLink
        v-else
        :to="{
          name: 'catalog-category',
          params: { categoryId: node.id },
          query: { locale },
        }"
        class="min-w-0 break-words text-sm underline underline-offset-4"
        >{{ categoryLabel(node) }}</RouterLink
      >
    </div>
    <ul
      v-if="open && node.children.length"
      class="ml-4 mt-2 flex flex-col gap-2 border-l pl-2"
    >
      <CategoryTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :locale="locale"
        :depth="depth + 1"
        :selectable="selectable"
        :selected="selected"
        :disabled="disabled"
        @toggle="$emit('toggle', $event)"
      />
    </ul>
  </li>
</template>
