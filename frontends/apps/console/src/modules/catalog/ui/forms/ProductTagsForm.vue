<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { CatalogTag } from "../../model/catalog.types";
const props = defineProps<{
  ids: string[];
  tags: CatalogTag[];
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [ids: string[]];
  dirty: [value: boolean];
}>();
const ids = ref([...props.ids]),
  dirty = ref(false);
function resetFields() {
  ids.value = [...props.ids];
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
</script>
<template>
  <form class="space-y-4" @submit.prevent="emit('submit', ids)">
    <fieldset class="space-y-2" :disabled="pending || disabled">
      <legend class="mb-2 font-medium">Назначенные метки</legend>
      <p v-if="!tags.length">Метки ещё не созданы.</p>
      <label v-for="t in tags" :key="t.id" class="flex items-center gap-2"
        ><input
          v-model="ids"
          type="checkbox"
          :value="t.id"
          :aria-label="t.label ?? t.id"
          @change="
            dirty = true;
            emit('dirty', true);
          "
        />{{ t.label ?? t.id }}</label
      >
    </fieldset>
    <div class="flex flex-wrap gap-2">
      <Button :disabled="pending || disabled">Сохранить метки</Button
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
