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
import StockLocationTypeSelect from "./StockLocationTypeSelect.vue";
import type {
  StockLocationCreateFormValues,
  StockLocationFieldErrors,
  StockLocationType,
} from "../../model/stock-location.types";
const props = defineProps<{
  open: boolean;
  values: StockLocationCreateFormValues;
  errors: StockLocationFieldErrors;
  pending: boolean;
  disabled: boolean;
  canCreate: boolean;
  uncertain: boolean;
  error: string;
}>();
const emit = defineEmits<{
  close: [];
  change: [values: StockLocationCreateFormValues];
  submit: [];
  check: [];
}>();
function change(field: "code" | "name", value: string | number): void {
  emit("change", { ...props.values, [field]: String(value) });
}
function changeType(value: StockLocationType | null): void {
  emit("change", { ...props.values, locationType: value ?? "" });
}
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')"
    ><DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
    >
      <DialogHeader
        ><DialogTitle>Создать локацию</DialogTitle
        ><DialogDescription
          >Укажите код, название и тип. Новая локация будет
          активна.</DialogDescription
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
            ><FieldLabel for="stock-location-create-code"
              >Код локации</FieldLabel
            ><Input
              id="stock-location-create-code"
              :model-value="values.code"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.code"
              aria-describedby="stock-location-create-code-error"
              autocomplete="off"
              autocapitalize="none"
              spellcheck="false"
              @update:model-value="change('code', $event)" /><FieldError
              id="stock-location-create-code-error"
              :errors="[errors.code]"
          /></Field>
          <Field
            :data-invalid="!!errors.name"
            :data-disabled="pending || disabled || uncertain"
            ><FieldLabel for="stock-location-create-name"
              >Название локации</FieldLabel
            ><Input
              id="stock-location-create-name"
              :model-value="values.name"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.name"
              aria-describedby="stock-location-create-name-error"
              autocomplete="off"
              @update:model-value="change('name', $event)" /><FieldError
              id="stock-location-create-name-error"
              :errors="[errors.name]"
          /></Field>
          <Field
            :data-invalid="!!errors.locationType"
            :data-disabled="pending || disabled || uncertain"
            ><FieldLabel for="stock-location-create-type"
              >Тип локации</FieldLabel
            ><StockLocationTypeSelect
              id="stock-location-create-type"
              label="Тип локации"
              :value="values.locationType || null"
              :disabled="pending || disabled || uncertain"
              :invalid="!!errors.locationType"
              @change="changeType" /><FieldError
              :errors="[errors.locationType]"
          /></Field>
          <Field
            :data-invalid="!!errors.parentLocationId"
            :data-disabled="pending || disabled || uncertain"
            ><FieldLabel for="stock-location-create-parent"
              >Родительская локация</FieldLabel
            ><slot name="parent" /><FieldDescription
              >Без родителя — корневая локация. Неактивный родитель
              допустим.</FieldDescription
            ><FieldError :errors="[errors.parentLocationId]"
          /></Field> </FieldGroup
        ><Alert v-if="error" variant="destructive"
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
          ><Button
            v-else
            type="submit"
            :disabled="disabled || pending || !canCreate"
            >{{ pending ? "Создание…" : "Создать" }}</Button
          ></DialogFooter
        >
      </form>
    </DialogContent></Dialog
  >
</template>
