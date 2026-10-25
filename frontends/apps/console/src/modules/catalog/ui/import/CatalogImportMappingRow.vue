<script setup lang="ts">
import { X } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  importTargets,
  localizedImportTargets,
} from "../../model/import.constants";
import type { ImportMapping, ImportField } from "../../model/import.types";
defineProps<{
  value: ImportMapping;
  index: number;
  fields: ImportField[];
  defaultLocale: string;
  pending: boolean;
}>();
defineEmits<{ change: [patch: Partial<ImportMapping>]; remove: [] }>();
</script>
<template>
  <div
    class="grid min-w-0 grid-cols-[minmax(0,1fr)_5rem_2.75rem] items-start gap-3 border-b py-4 last:border-b-0 sm:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_5rem_2.75rem]"
  >
    <Field class="col-span-2 min-w-0 gap-2 sm:col-span-1">
      <FieldLabel
        :for="`import-source-${index}`"
        class="text-xs text-muted-foreground"
        >Исходное поле {{ index + 1 }}</FieldLabel
      >
      <Select
        :model-value="value.source ?? '__constant'"
        :disabled="pending"
        @update:model-value="
          (v) =>
            $emit(
              'change',
              v === '__constant'
                ? { source: null, constant: '' }
                : { source: String(v), constant: null },
            )
        "
      >
        <SelectTrigger
          :id="`import-source-${index}`"
          class="h-11 min-h-11 w-full min-w-0"
          :aria-label="`Источник ${index + 1}`"
          ><SelectValue
        /></SelectTrigger>
        <SelectContent
          ><SelectGroup
            ><SelectItem value="__constant">Постоянное значение</SelectItem
            ><SelectItem
              v-for="(field, column) in fields"
              :key="field.id"
              :value="field.id"
              >{{ column + 1 }}. {{ field.label }}</SelectItem
            ></SelectGroup
          ></SelectContent
        >
      </Select>
      <Input
        v-if="value.constant !== null"
        class="h-11"
        :aria-label="`Константа ${index + 1}`"
        placeholder="Постоянное значение"
        :model-value="value.constant"
        :disabled="pending"
        @update:model-value="(v) => $emit('change', { constant: String(v) })"
      />
    </Field>
    <Field
      class="row-start-2 min-w-0 gap-2 sm:col-start-2 sm:row-start-1"
      :class="{
        'col-span-3 sm:col-span-1': !localizedImportTargets.has(value.target),
      }"
    >
      <FieldLabel
        :for="`import-target-${index}`"
        class="text-xs text-muted-foreground"
        >Поле в системе</FieldLabel
      >
      <Select
        :model-value="value.target"
        :disabled="pending"
        @update:model-value="(v) => $emit('change', { target: String(v) })"
      >
        <SelectTrigger
          :id="`import-target-${index}`"
          class="h-11 min-h-11 w-full min-w-0"
          :aria-label="`Поле Catalog ${index + 1}`"
          ><SelectValue
        /></SelectTrigger>
        <SelectContent
          ><SelectGroup
            ><SelectItem
              v-for="[key, label] in importTargets"
              :key="key"
              :value="key"
              >{{ label }}</SelectItem
            ></SelectGroup
          ></SelectContent
        >
      </Select>
    </Field>
    <Field
      v-if="localizedImportTargets.has(value.target)"
      class="col-span-2 col-start-2 row-start-2 min-w-0 gap-2 sm:col-span-1 sm:col-start-3 sm:row-start-1"
    >
      <FieldLabel
        :for="`import-locale-${index}`"
        class="text-xs text-muted-foreground"
        >Язык</FieldLabel
      >
      <Input
        :id="`import-locale-${index}`"
        class="h-11 min-w-0"
        :aria-label="`Язык ${index + 1}`"
        :placeholder="value.target === 'images' ? 'Все языки' : defaultLocale"
        :model-value="value.locale ?? ''"
        :disabled="pending"
        @update:model-value="
          (v) => $emit('change', { locale: String(v) || null })
        "
      />
    </Field>
    <Button
      type="button"
      variant="ghost"
      size="icon"
      class="col-start-3 row-start-1 mt-6 size-11 sm:col-start-4"
      :disabled="pending"
      :aria-label="`Не импортировать ${value.target} ${index + 1}`"
      @click="$emit('remove')"
      ><X
    /></Button>
  </div>
</template>
