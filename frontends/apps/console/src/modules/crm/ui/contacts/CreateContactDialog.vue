<script setup lang="ts">
import { ref, watch } from "vue";
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
import type { ContactInput } from "../../model/crm.types";

const props = defineProps<{ open: boolean; pending: boolean }>();
const emit = defineEmits<{
  "update:open": [open: boolean];
  submit: [input: ContactInput];
}>();
const firstName = ref("");
const lastName = ref("");
const middleName = ref("");
const attempted = ref(false);
watch(
  () => props.open,
  (open) => {
    if (!open) return;
    firstName.value = "";
    lastName.value = "";
    middleName.value = "";
    attempted.value = false;
  },
);
function submit() {
  attempted.value = true;
  const first = firstName.value.trim();
  if (!first || first.length > 255 || props.pending) return;
  emit("submit", {
    firstName: first,
    lastName: lastName.value.trim() || null,
    middleName: middleName.value.trim() || null,
  });
}
</script>

<template>
  <Dialog :open="open" @update:open="!pending && emit('update:open', $event)">
    <DialogContent
      ><form class="flex flex-col gap-4" @submit.prevent="submit">
        <DialogHeader
          ><DialogTitle>Новый контакт</DialogTitle>
          <DialogDescription
            >Сначала создайте контакт. Связи и контактные данные можно добавить
            на его странице.</DialogDescription
          >
        </DialogHeader>
        <FieldGroup>
          <Field
            :data-invalid="attempted && !firstName.trim() ? true : undefined"
          >
            <FieldLabel for="new-contact-first-name">Имя</FieldLabel>
            <Input
              id="new-contact-first-name"
              v-model="firstName"
              maxlength="255"
              required
              :aria-invalid="attempted && !firstName.trim()"
              :disabled="pending"
            />
            <FieldError v-if="attempted && !firstName.trim()"
              >Укажите имя.</FieldError
            >
          </Field>
          <Field
            ><FieldLabel for="new-contact-last-name">Фамилия</FieldLabel
            ><Input
              id="new-contact-last-name"
              v-model="lastName"
              maxlength="255"
              :disabled="pending"
          /></Field>
          <Field
            ><FieldLabel for="new-contact-middle-name">Отчество</FieldLabel
            ><Input
              id="new-contact-middle-name"
              v-model="middleName"
              maxlength="255"
              :disabled="pending"
          /></Field>
        </FieldGroup>
        <DialogFooter
          ><Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('update:open', false)"
            >Отмена</Button
          >
          <Button type="submit" :disabled="pending"
            ><Spinner v-if="pending" data-icon="inline-start" />Создать</Button
          ></DialogFooter
        >
      </form></DialogContent
    >
  </Dialog>
</template>
