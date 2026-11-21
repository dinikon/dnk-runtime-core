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
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  WarehouseCreateValues,
  WarehouseFieldErrors,
} from "../../model/warehouse.types";
const props = defineProps<{
  open: boolean;
  values: WarehouseCreateValues;
  errors: WarehouseFieldErrors;
  pending: boolean;
  disabled: boolean;
  uncertain: boolean;
  error: string;
}>();
const emit = defineEmits<{
  close: [];
  change: [values: WarehouseCreateValues];
  submit: [];
  check: [];
}>();
function change(
  field: keyof WarehouseCreateValues,
  value: string | number,
): void {
  emit("change", { ...props.values, [field]: String(value) });
}
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')">
    <DialogContent
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
    >
      <DialogHeader
        ><DialogTitle>Создать склад</DialogTitle
        ><DialogDescription
          >Укажите код и название. Основная зона хранения будет создана
          автоматически.</DialogDescription
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
            <FieldLabel for="warehouse-create-code">Код склада</FieldLabel>
            <Input
              id="warehouse-create-code"
              :model-value="values.code"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.code"
              aria-describedby="warehouse-create-code-error"
              autocomplete="off"
              autocapitalize="none"
              spellcheck="false"
              @update:model-value="change('code', $event)"
            />
            <FieldError
              id="warehouse-create-code-error"
              :errors="[errors.code]"
            />
          </Field>
          <Field
            :data-invalid="!!errors.name"
            :data-disabled="pending || disabled || uncertain"
          >
            <FieldLabel for="warehouse-create-name">Название склада</FieldLabel>
            <Input
              id="warehouse-create-name"
              :model-value="values.name"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.name"
              aria-describedby="warehouse-create-name-error"
              autocomplete="off"
              @update:model-value="change('name', $event)"
            />
            <FieldError
              id="warehouse-create-name-error"
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
