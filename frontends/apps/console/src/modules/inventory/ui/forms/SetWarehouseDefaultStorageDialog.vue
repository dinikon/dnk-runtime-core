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
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
defineProps<{
  open: boolean;
  pending: boolean;
  canSubmit: boolean;
  error: string;
  fieldError?: string;
  uncertain: boolean;
  checking: boolean;
}>();
const emit = defineEmits<{ close: []; submit: []; check: [] }>();
</script>

<template>
  <Dialog
    :open="open"
    @update:open="!$event && !pending && !checking && emit('close')"
  >
    <DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :show-close-button="!pending && !checking"
      @escape-key-down="(pending || checking) && $event.preventDefault()"
      @interact-outside="(pending || checking) && $event.preventDefault()"
    >
      <DialogHeader>
        <DialogTitle>Основная локация хранения</DialogTitle>
        <DialogDescription
          >Выберите активную локацию хранения этого склада. Прежняя локация
          сохранится.</DialogDescription
        >
      </DialogHeader>
      <form
        class="flex flex-col gap-5"
        novalidate
        :aria-busy="pending || checking"
        @submit.prevent="emit('submit')"
      >
        <FieldGroup>
          <Field
            :data-invalid="!!fieldError"
            :data-disabled="pending || checking"
          >
            <FieldLabel for="default-storage-location"
              >Локация хранения</FieldLabel
            >
            <slot />
            <FieldDescription id="default-storage-location-hint"
              >Доступны корневые и дочерние локации типа STORAGE. Склад может
              быть неактивным.</FieldDescription
            >
            <FieldError
              id="default-storage-location-error"
              :errors="[fieldError]"
            />
          </Field>
        </FieldGroup>
        <Alert v-if="error" variant="destructive"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        >
        <DialogFooter class="gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="pending || checking"
            @click="emit('close')"
            >Отмена</Button
          >
          <Button
            v-if="uncertain"
            type="button"
            :disabled="pending || checking"
            @click="emit('check')"
            >{{ checking ? "Проверка…" : "Проверить назначение" }}</Button
          >
          <Button
            v-else
            type="submit"
            :disabled="pending || checking || !canSubmit"
            >{{ pending ? "Назначение…" : "Назначить" }}</Button
          >
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
