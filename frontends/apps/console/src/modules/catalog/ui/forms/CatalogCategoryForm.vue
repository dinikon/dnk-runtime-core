<script setup lang="ts">
import { computed, ref } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import type {
  CategoryOption,
  CategoryChange,
} from "../../model/category.types";
const props = defineProps<{
  node?: CategoryOption;
  locale: string;
  options: CategoryOption[];
  pending: boolean;
  error: string;
}>();
const emit = defineEmits<{
  save: [value: CategoryChange];
  cancel: [];
  dirty: [value: boolean];
}>();
const name = ref(props.node?.name ?? ""),
  parent = ref(props.node?.parentId ?? "");
const changed = computed(
  () =>
    name.value !== (props.node?.name ?? "") ||
    parent.value !== (props.node?.parentId ?? ""),
);
const parents = computed(() => {
  if (!props.node) return props.options;
  const excluded = new Set([props.node.id]);
  return props.options.filter((node) => {
    if (node.parentId && excluded.has(node.parentId)) excluded.add(node.id);
    return !excluded.has(node.id);
  });
});
function submit(): void {
  if (props.pending) return;
  if (!props.node) {
    emit("save", {
      action: "create",
      locale: props.locale,
      name: name.value,
      parent: parent.value || null,
    });
    return;
  }
  emit("save", {
    action: "update",
    id: props.node.id,
    translations:
      name.value !== (props.node.name ?? "")
        ? { [props.locale]: name.value }
        : undefined,
    parent:
      parent.value !== (props.node.parentId ?? "")
        ? parent.value || null
        : undefined,
  });
}
</script>
<template>
  <form
    class="grid max-w-xl gap-4 rounded-lg border p-4"
    @submit.prevent="submit"
  >
    <h2 class="font-semibold">
      {{ node ? "Редактировать категорию" : "Новая категория" }}
    </h2>
    <p v-if="node && !node.name" class="text-sm text-muted-foreground">
      Исходное название ({{ node.sourceLocale }}) · {{ node.sourceName }}
    </p>
    <fieldset :disabled="pending" class="grid gap-3">
      <label class="grid gap-1 text-sm"
        >Название ({{ locale }})
        <Input
          v-model="name"
          maxlength="255"
          @update:model-value="emit('dirty', true)"
        />
      </label>
      <label class="grid gap-1 text-sm"
        >Родительская категория
        <NativeSelect
          aria-label="Родительская категория"
          v-model="parent"
          @update:model-value="emit('dirty', true)"
        >
          <option value="">Корень дерева</option>
          <option v-for="row in parents" :key="row.id" :value="row.id">
            {{ row.path }}
          </option>
        </NativeSelect>
      </label>
    </fieldset>
    <p v-if="error" role="alert" class="text-sm text-destructive">
      {{ error }}
    </p>
    <div class="flex gap-2">
      <Button
        type="submit"
        :disabled="
          pending ||
          !changed ||
          ((!node || name !== (node.name ?? '')) && !name.trim())
        "
        >Сохранить</Button
      >
      <Button
        variant="outline"
        type="button"
        :disabled="pending"
        @click="emit('cancel')"
        >Отмена</Button
      >
    </div>
  </form>
</template>
