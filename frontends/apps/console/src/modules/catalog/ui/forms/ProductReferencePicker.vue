<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { Plus, X } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldSet,
  FieldLegend,
} from "@/components/ui/field";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
const props = defineProps<{
  ids: string[];
  options: { id: string; label: string }[];
  label: string;
  disabled: boolean;
}>();
const emit = defineEmits<{ change: [ids: string[]] }>();
const search = ref("");
const id = useId();
const filtered = computed(() =>
  props.options.filter((option) =>
    option.label.toLocaleLowerCase().includes(search.value.toLocaleLowerCase()),
  ),
);
function toggle(value: string, checked: boolean): void {
  emit(
    "change",
    checked
      ? [...new Set([...props.ids, value])]
      : props.ids.filter((entry) => entry !== value),
  );
}
</script>
<template>
  <FieldSet class="min-w-0 gap-3"
    ><FieldLegend variant="label">{{ label }}</FieldLegend>
    <div v-if="ids.length" class="flex min-w-0 flex-col gap-1">
      <div
        v-for="value in ids"
        :key="value"
        class="flex min-w-0 items-center justify-between gap-2 rounded-md bg-muted/50 pl-3"
      >
        <span class="min-w-0 break-words text-sm">{{
          options.find((entry) => entry.id === value)?.label ?? "Нет перевода"
        }}</span
        ><Button
          type="button"
          variant="ghost"
          size="icon"
          class="min-h-11 min-w-11 shrink-0"
          :disabled="disabled"
          :aria-label="`Убрать: ${options.find((entry) => entry.id === value)?.label ?? 'Нет перевода'}`"
          @click="toggle(value, false)"
          ><X
        /></Button>
      </div>
    </div>
    <p v-else class="text-sm text-muted-foreground">Ничего не выбрано.</p>
    <Popover
      ><PopoverTrigger as-child
        ><Button
          type="button"
          variant="outline"
          class="min-h-11 w-full justify-start"
          :disabled="disabled"
          ><Plus data-icon="inline-start" />Выбрать значения</Button
        ></PopoverTrigger
      ><PopoverContent
        align="start"
        class="product-reference-popover flex flex-col gap-3"
      >
        <Field
          ><FieldLabel :for="`${id}-search`">{{ label }}</FieldLabel
          ><Input
            :id="`${id}-search`"
            v-model="search"
            placeholder="Поиск…"
            autocomplete="off"
        /></Field>
        <FieldGroup class="max-h-64 gap-1 overflow-y-auto overscroll-contain"
          ><Field
            v-for="option in filtered"
            :key="option.id"
            orientation="horizontal"
            class="min-h-11 gap-3"
            ><Checkbox
              :id="`${id}-${option.id}`"
              :model-value="ids.includes(option.id)"
              :disabled="disabled"
              @update:model-value="toggle(option.id, $event === true)"
            /><FieldLabel
              :for="`${id}-${option.id}`"
              class="min-h-11 min-w-0 flex-1 break-words"
              >{{ option.label }}</FieldLabel
            ></Field
          >
          <p v-if="!filtered.length" class="py-3 text-sm text-muted-foreground">
            {{
              options.length ? "Ничего не найдено." : "Справочник пока пуст."
            }}
          </p></FieldGroup
        >
      </PopoverContent></Popover
    >
  </FieldSet>
</template>
