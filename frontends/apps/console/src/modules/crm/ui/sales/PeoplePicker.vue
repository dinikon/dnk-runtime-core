<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { FieldSet, FieldLegend } from "@/components/ui/field";
const props = defineProps<{
  label: string;
  options: { id: string; label: string }[];
  modelValue: string[];
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();
const search = ref(""),
  prefix = useId();
const visible = computed(() => {
  const options = props.disabled
    ? props.modelValue.map(
        (id) =>
          props.options.find((option) => option.id === id) ?? {
            id,
            label: "Связанный участник",
          },
      )
    : props.options;
  return options.filter((o) =>
    o.label.toLocaleLowerCase().includes(search.value.toLocaleLowerCase()),
  );
});
function toggle(id: string, v: unknown) {
  emit(
    "update:modelValue",
    v
      ? [...new Set([...props.modelValue, id])]
      : props.modelValue.filter((i) => i !== id),
  );
}
</script>
<template>
  <FieldSet
    ><FieldLegend>{{ label }}</FieldLegend
    ><Input
      v-if="!disabled"
      v-model="search"
      :aria-label="'Поиск: ' + label"
      placeholder="Найти по имени или названию"
      :disabled="disabled"
    />
    <div
      class="flex max-h-44 flex-col gap-2 overflow-auto rounded-md border p-3"
    >
      <label
        v-for="o in visible"
        :key="o.id"
        :for="prefix + o.id"
        class="flex items-center gap-2 text-sm"
        ><Checkbox
          :id="prefix + o.id"
          :model-value="modelValue.includes(o.id)"
          :disabled="disabled"
          @update:model-value="toggle(o.id, $event)"
        />{{ o.label }}</label
      >
      <p v-if="!visible.length" class="text-sm text-muted-foreground">
        {{ disabled ? "Участники не выбраны." : "Нет доступных записей." }}
      </p>
    </div></FieldSet
  >
</template>
