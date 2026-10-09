<script setup lang="ts">
import { watch } from "vue";
import { useForm } from "vee-validate";
import { toTypedSchema } from "@vee-validate/zod";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { DefinitionInput } from "../../model/catalog.types";
const props = defineProps<{
  block: boolean;
  code?: string;
  label?: string | null;
  valueType?: "text" | "rich_text";
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [input: DefinitionInput];
  dirty: [value: boolean];
  cancel: [];
}>();
const { defineField, handleSubmit, errors, meta, resetForm } = useForm({
  validationSchema: toTypedSchema(
    z.object({
      code: z
        .string()
        .regex(/^[a-z][a-z0-9_]{0,63}$/, "Код: a-z, 0-9, _; до 64 символов"),
      label: z.string().trim().min(1, "Заполните подпись").max(255),
      valueType: z.enum(["text", "rich_text"]),
    }),
  ),
  initialValues: {
    code: props.code ?? "",
    label: props.label ?? "",
    valueType: props.valueType ?? "text",
  },
});
const [codeInput] = defineField("code"),
  [labelInput] = defineField("label"),
  [valueTypeInput] = defineField("valueType");
watch(
  () => meta.value.dirty,
  (v) => emit("dirty", v),
);
watch(
  () => props.reset,
  () =>
    resetForm({
      values: {
        code: props.code ?? "",
        label: props.label ?? "",
        valueType: props.valueType ?? "text",
      },
    }),
);
const submit = handleSubmit((values) => emit("submit", values));
</script>
<template>
  <form class="space-y-4" @submit="submit">
    <label class="block space-y-2"
      ><span>Стабильный код</span
      ><Input
        v-model="codeInput"
        aria-label="Стабильный код"
        :disabled="!!props.code || pending || disabled"
      /><span v-if="errors.code" class="text-sm text-destructive">{{
        errors.code
      }}</span></label
    ><label class="block space-y-2"
      ><span>Подпись выбранного языка</span
      ><Input
        v-model="labelInput"
        aria-label="Подпись"
        :disabled="pending || disabled"
      /><span v-if="errors.label" class="text-sm text-destructive">{{
        errors.label
      }}</span></label
    ><label v-if="block" class="block space-y-2"
      ><span>Тип значения</span
      ><select
        v-model="valueTypeInput"
        aria-label="Тип значения"
        class="block rounded-md border bg-background p-2"
        :disabled="pending || disabled"
      >
        <option value="text">Текст</option>
        <option value="rich_text">Форматированный текст (HTML)</option>
      </select></label
    >
    <div class="flex gap-2">
      <Button type="submit" :disabled="pending || disabled">{{
        pending ? "Сохранение…" : "Сохранить"
      }}</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="pending"
        @click="
          resetForm();
          emit('cancel');
        "
        >Отменить</Button
      >
    </div>
  </form>
</template>
