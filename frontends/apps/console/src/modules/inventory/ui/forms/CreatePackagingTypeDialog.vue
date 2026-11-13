<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldError,
  FieldDescription,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  PackagingTypeCreateValues,
  PackagingTypeFieldErrors,
} from "../../model/packaging-type.types";
const props = defineProps<{
  open: boolean;
  values: PackagingTypeCreateValues;
  errors: PackagingTypeFieldErrors;
  pending: boolean;
  disabled: boolean;
  uncertain: boolean;
  error: string;
}>();
const emit = defineEmits<{
  close: [];
  change: [values: PackagingTypeCreateValues];
  submit: [];
  check: [];
}>();
function change(
  field: keyof PackagingTypeCreateValues,
  value: string | number,
): void {
  emit("change", { ...props.values, [field]: String(value) });
}
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')">
    <DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
    >
      <DialogHeader
        ><DialogTitle>Создать тип тары</DialogTitle
        ><DialogDescription
          >Укажите код и название. Новый тип тары будет
          активен.</DialogDescription
        ></DialogHeader
      >
      <form
        class="flex flex-col gap-5"
        novalidate
        :aria-busy="pending"
        @submit.prevent="emit('submit')"
      >
        <FieldGroup>
          <Field
            :data-invalid="!!errors.code"
            :data-disabled="pending || disabled || uncertain"
          >
            <FieldLabel for="packaging-type-create-code"
              >Код типа тары</FieldLabel
            >
            <Input
              id="packaging-type-create-code"
              :model-value="values.code"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.code"
              aria-describedby="packaging-type-create-code-hint packaging-type-create-code-error"
              autocomplete="off"
              autocapitalize="none"
              spellcheck="false"
              @update:model-value="change('code', $event)"
            />
            <FieldDescription id="packaging-type-create-code-hint"
              >Регистр значим: BOX и box — разные коды.</FieldDescription
            >
            <FieldError
              id="packaging-type-create-code-error"
              :errors="[errors.code]"
            />
          </Field>
          <Field
            :data-invalid="!!errors.name"
            :data-disabled="pending || disabled || uncertain"
          >
            <FieldLabel for="packaging-type-create-name"
              >Название типа тары</FieldLabel
            >
            <Input
              id="packaging-type-create-name"
              :model-value="values.name"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.name"
              aria-describedby="packaging-type-create-name-error"
              autocomplete="off"
              @update:model-value="change('name', $event)"
            />
            <FieldError
              id="packaging-type-create-name-error"
              :errors="[errors.name]"
            />
          </Field>
        </FieldGroup>
        <Alert v-if="error" variant="destructive"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        >
        <DialogFooter class="gap-2"
          ><Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('close')"
            >Отмена</Button
          ><Button
            v-if="uncertain"
            type="button"
            :disabled="disabled"
            @click="emit('check')"
            >Проверить список</Button
          ><Button v-else type="submit" :disabled="disabled || pending">{{
            pending ? "Создание…" : "Создать"
          }}</Button></DialogFooter
        >
      </form>
    </DialogContent>
  </Dialog>
</template>
