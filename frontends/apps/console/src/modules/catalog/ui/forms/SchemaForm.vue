<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { ContentBlock, BlockLink } from "../../model/catalog.types";
const props = defineProps<{
  links: BlockLink[];
  blocks: ContentBlock[];
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [links: BlockLink[]];
  dirty: [value: boolean];
}>();
const links = ref(props.links.map((b) => ({ ...b }))),
  selected = ref(""),
  scope = ref<"PRODUCT" | "VARIANT">("PRODUCT");
function resetFields() {
  links.value = props.links.map((b) => ({ ...b }));
  emit("dirty", false);
}
watch(() => props.reset, resetFields);
function changed() {
  emit("dirty", true);
}
function add() {
  if (
    !selected.value ||
    links.value.some(
      (b) => b.blockId === selected.value && b.scope === scope.value,
    )
  )
    return;
  links.value.push({
    blockId: selected.value,
    scope: scope.value,
    required: false,
    position: links.value.filter((b) => b.scope === scope.value).length,
  });
  changed();
}
function move(index: number, delta: number) {
  const row = links.value[index];
  if (!row) return;
  const other = links.value
    .map((b, i) => ({ b, i }))
    .filter(({ b }) => b.scope === row.scope);
  const pos = other.findIndex(({ i }) => i === index),
    neighbor = other[pos + delta];
  if (!neighbor) return;
  [links.value[index], links.value[neighbor.i]] = [neighbor.b, row];
  changed();
}
function submit() {
  const counts = { PRODUCT: 0, VARIANT: 0 };
  emit(
    "submit",
    links.value.map((b) => ({ ...b, position: counts[b.scope]++ })),
  );
}
</script>
<template>
  <form class="space-y-4" @submit.prevent="submit">
    <p class="text-sm text-muted-foreground">
      PRODUCT задаёт контент товара. VARIANT задаёт контент вариантов VARIABLE;
      SIMPLE использует только PRODUCT. Обязательность и порядок задаются
      отдельно.
    </p>
    <fieldset :disabled="disabled || pending" class="space-y-3">
      <div
        v-for="(link, index) in links"
        :key="link.blockId + link.scope"
        class="flex flex-wrap items-center gap-3 rounded-md border p-3"
      >
        <span class="flex-1"
          >{{ link.scope }} ·
          {{
            blocks.find((b) => b.id === link.blockId)?.label ??
            blocks.find((b) => b.id === link.blockId)?.code ??
            link.blockId
          }}</span
        ><label class="flex gap-2 text-sm"
          ><input
            v-model="link.required"
            type="checkbox"
            @change="changed"
          />Обязательный</label
        ><button type="button" aria-label="Выше" @click="move(index, -1)">
          ↑</button
        ><button type="button" aria-label="Ниже" @click="move(index, 1)">
          ↓</button
        ><button
          type="button"
          aria-label="Убрать блок"
          @click="
            links.splice(index, 1);
            changed();
          "
        >
          ×
        </button>
      </div>
      <div class="flex flex-wrap gap-2">
        <select
          v-model="selected"
          aria-label="Добавить блок"
          class="max-w-full rounded-md border bg-background p-2"
        >
          <option value="">Выберите блок</option>
          <option v-for="block in blocks" :key="block.id" :value="block.id">
            {{ block.label ?? block.code }}
          </option></select
        ><select
          v-model="scope"
          aria-label="Область блока"
          class="rounded-md border bg-background p-2"
        >
          <option>PRODUCT</option>
          <option>VARIANT</option></select
        ><Button variant="outline" type="button" @click="add">Добавить</Button>
      </div>
    </fieldset>
    <div class="flex gap-2">
      <Button type="submit" :disabled="pending || disabled"
        >Сохранить схему</Button
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
