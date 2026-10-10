<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { CatalogCategory } from "../../model/catalog.types";
const props = defineProps<{
  ids: string[];
  primaryId: string | null;
  categories: CatalogCategory[];
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [ids: string[], primaryId: string | null];
  dirty: [value: boolean];
}>();
const ids = ref([...props.ids]),
  primary = ref(props.primaryId ?? ""),
  dirty = ref(false);
function mark() {
  if (!ids.value.includes(primary.value)) primary.value = "";
  dirty.value = true;
  emit("dirty", true);
}
function resetFields() {
  ids.value = [...props.ids];
  primary.value = props.primaryId ?? "";
  dirty.value = false;
  emit("dirty", false);
}
watch(() => props.reset, resetFields);
watch(
  () => props.ids,
  () => {
    if (!dirty.value) resetFields();
  },
);
function path(category: CatalogCategory): string {
  const names = [category.label ?? category.id];
  const seen = new Set([category.id]);
  let parent = category.parentId;
  while (parent) {
    if (seen.has(parent)) break;
    seen.add(parent);
    const c = props.categories.find((c) => c.id === parent);
    if (!c) break;
    names.unshift(c.label ?? c.id);
    parent = c.parentId;
  }
  return names.join(" / ");
}
</script>
<template>
  <form
    class="space-y-4"
    @submit.prevent="emit('submit', ids, primary || null)"
  >
    <p class="text-sm text-muted-foreground">
      Выберите явные категории и одну основную. Родители не назначаются
      автоматически.
    </p>
    <fieldset class="space-y-2" :disabled="pending || disabled">
      <legend class="mb-2 font-medium">Назначенные категории</legend>
      <p v-if="!categories.length">Категории ещё не созданы.</p>
      <label
        v-for="c in categories"
        :key="c.id"
        class="flex items-start gap-2 break-words"
        ><input
          v-model="ids"
          type="checkbox"
          :value="c.id"
          :aria-label="path(c)"
          class="mt-1"
          @change="mark"
        /><span>{{ path(c) }}</span></label
      >
    </fieldset>
    <label v-if="ids.length" class="block space-y-2"
      ><span>Основная категория</span
      ><select
        v-model="primary"
        aria-label="Основная категория"
        required
        :disabled="pending || disabled"
        class="w-full rounded-md border bg-background p-2"
        @change="
          dirty = true;
          emit('dirty', true);
        "
      >
        <option value="" disabled>Выберите основную</option>
        <option
          v-for="c in categories.filter((c) => ids.includes(c.id))"
          :key="c.id"
          :value="c.id"
        >
          {{ path(c) }}
        </option>
      </select></label
    >
    <div class="flex flex-wrap gap-2">
      <Button :disabled="pending || disabled || (!!ids.length && !primary)"
        >Сохранить категории</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="pending || disabled"
        @click="
          ids = [];
          primary = '';
          mark();
        "
        >Очистить набор</Button
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
