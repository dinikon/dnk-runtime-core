<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import type { CatalogTag } from "../../model/catalog.types";
const props = defineProps<{
  ids: string[];
  tags: CatalogTag[];
  pending: boolean;
  disabled: boolean;
  reset: number;
  validationError?: string;
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
            nextTick(() => emit('submit', ids));
          "
        />{{ t.label ?? t.id }}</label
      >
    </fieldset>
    <p v-if="validationError" role="alert" class="text-sm text-destructive">
      {{ validationError }}
    </p>
  </form>
</template>
