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
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

defineProps<{
  open: boolean;
  sku: string;
  pending: boolean;
  disabled: boolean;
  error: string;
  skuError: string;
  uncertain: boolean;
}>();
const emit = defineEmits<{
  close: [];
  sku: [value: string];
  submit: [];
  check: [];
}>();
</script>

<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')">
    <DialogContent
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
    >
      <DialogHeader>
        <DialogTitle>Создать складскую позицию</DialogTitle>
        <DialogDescription
          >Укажите код SKU. Настройки складского учёта будут заданы
          автоматически; их можно изменить после создания.</DialogDescription
        >
      </DialogHeader>
      <form
        class="flex flex-col gap-5"
        novalidate
        :aria-busy="pending"
        @submit.prevent="emit('submit')"
      >
        <FieldGroup>
          <Field
            :data-invalid="!!skuError"
            :data-disabled="pending || disabled || uncertain"
          >
            <FieldLabel for="inventory-create-sku">Код SKU</FieldLabel>
            <Input
              id="inventory-create-sku"
              :model-value="sku"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!skuError"
              aria-describedby="inventory-create-hint inventory-create-error"
              autocomplete="off"
              autocapitalize="none"
              spellcheck="false"
              @update:model-value="emit('sku', String($event))"
            />
            <FieldDescription id="inventory-create-hint"
              >Уникальный ручной код складской позиции.</FieldDescription
            >
            <FieldError id="inventory-create-error" :errors="[skuError]" />
          </Field>
        </FieldGroup>
        <Alert v-if="error" variant="destructive"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        >
        <DialogFooter class="gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('close')"
            >Отмена</Button
          >
          <Button
            v-if="uncertain"
            type="button"
            :disabled="disabled"
            @click="emit('check')"
            >Проверить список</Button
          >
          <Button v-else type="submit" :disabled="pending || disabled">{{
            pending ? "Создание…" : "Создать"
          }}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
