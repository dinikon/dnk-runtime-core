<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { Contact, ContactInput } from "../../model/crm.types";

const props = defineProps<{
  open: boolean;
  contact: Contact | null;
  pending: boolean;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  submit: [input: ContactInput];
}>();

const firstName = ref("");
const lastName = ref("");
const middleName = ref("");
const attempted = ref(false);
const canSubmit = computed(
  () =>
    firstName.value.trim().length > 0 && firstName.value.trim().length <= 255,
);

watch(
  () => [props.open, props.contact] as const,
  ([open, contact]) => {
    if (!open) return;
    firstName.value = contact?.firstName ?? "";
    lastName.value = contact?.lastName ?? "";
    middleName.value = contact?.middleName ?? "";
    attempted.value = false;
  },
  { immediate: true },
);

function optionalName(value: string): string | null {
  return value.trim() || null;
}

function submit() {
  attempted.value = true;
  if (!canSubmit.value || props.pending) return;
  emit("submit", {
    firstName: firstName.value.trim(),
    lastName: optionalName(lastName.value),
    middleName: optionalName(middleName.value),
  });
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent>
      <form class="flex flex-col gap-4" @submit.prevent="submit">
        <DialogHeader>
          <DialogTitle>{{
            contact ? "Редактировать контакт" : "Новый контакт"
          }}</DialogTitle>
          <DialogDescription>
            Укажите имя и, при наличии, фамилию и отчество клиента.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field :data-invalid="attempted && !canSubmit ? true : undefined">
            <FieldLabel for="contact-first-name">Имя</FieldLabel>
            <Input
              id="contact-first-name"
              v-model="firstName"
              maxlength="255"
              autocomplete="given-name"
              required
              :aria-invalid="attempted && !canSubmit"
              :disabled="pending"
            />
            <FieldError v-if="attempted && !canSubmit">
              Имя обязательно и должно быть не длиннее 255 символов.
            </FieldError>
          </Field>
          <Field>
            <FieldLabel for="contact-last-name">Фамилия</FieldLabel>
            <Input
              id="contact-last-name"
              v-model="lastName"
              maxlength="255"
              autocomplete="family-name"
              :disabled="pending"
            />
          </Field>
          <Field>
            <FieldLabel for="contact-middle-name">Отчество</FieldLabel>
            <Input
              id="contact-middle-name"
              v-model="middleName"
              maxlength="255"
              autocomplete="additional-name"
              :disabled="pending"
            />
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('update:open', false)"
          >
            Отмена
          </Button>
          <Button type="submit" :disabled="pending">
            <Spinner v-if="pending" data-icon="inline-start" />
            {{ contact ? "Сохранить" : "Создать" }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
