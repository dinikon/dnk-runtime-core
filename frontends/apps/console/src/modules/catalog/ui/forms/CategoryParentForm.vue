<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { CatalogCategory } from "../../model/catalog.types";
const props = defineProps<{
  id: string;
  parentId: string | null;
  categories: CatalogCategory[];
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [parentId: string | null];
  dirty: [value: boolean];
}>();
const parent = ref(props.parentId ?? "");
watch(parent, (value) => emit("dirty", value !== (props.parentId ?? "")));
watch(
  () => props.reset,
  () => {
    parent.value = props.parentId ?? "";
    emit("dirty", false);
  },
);
function allowed(category: CatalogCategory) {
  const seen = new Set<string>();
  let node: CatalogCategory | undefined = category;
  while (node) {
    if (node.id === props.id || seen.has(node.id)) return false;
    seen.add(node.id);
    node = props.categories.find((c) => c.id === node?.parentId);
  }
  return true;
}
</script>
<template>
  <form class="space-y-4" @submit.prevent="emit('submit', parent || null)">
    <label class="block space-y-2"
      ><span>Родительская категория</span
      ><select
        v-model="parent"
        aria-label="Родительская категория"
        :disabled="pending || disabled"
        class="w-full rounded-md border bg-background p-2"
      >
        <option value="">Корень дерева</option>
        <option
          v-for="c in categories.filter(allowed)"
          :key="c.id"
          :value="c.id"
        >
          {{ c.label ?? c.id }}
        </option>
      </select></label
    >
    <p class="text-sm text-muted-foreground">
      Перемещение сохраняет дочерние категории и назначения товаров.
    </p>
    <div class="flex gap-2">
      <Button :disabled="pending || disabled || parent === (parentId ?? '')"
        >Переместить</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="pending"
        @click="parent = parentId ?? ''"
        >Отменить</Button
      >
    </div>
  </form>
</template>
