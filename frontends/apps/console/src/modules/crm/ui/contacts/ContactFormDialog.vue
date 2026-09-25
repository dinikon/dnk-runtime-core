<script setup lang="ts">
import {
  ContactPointsWidget,
  validateContactPoints,
} from "@/modules/contact-points";
import type {
  ContactPointDraft,
  ContactPointLabel,
  ContactPointErrors,
} from "@/modules/contact-points";
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
  labels: ContactPointLabel[];
  labelsLoading: boolean;
  labelsError: boolean;
  pointErrors: ContactPointErrors;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  submit: [input: ContactInput];
  retryLabels: [];
  clearPointErrors: [keys: string[]];
}>();

const firstName = ref("");
const lastName = ref("");
const middleName = ref("");
const attempted = ref(false);
const phones = ref<ContactPointDraft[]>([]);
const emails = ref<ContactPointDraft[]>([]);
const pointsValid = ref(true);
watch([phones, emails], (current, previous) => {
  const rows = new Map(current.flat().map((row) => [row.clientKey, row]));
  const changed = previous
    .flat()
    .filter((old) => {
      const row = rows.get(old.clientKey);
      return (
        !row ||
        row.value !== old.value ||
        row.countryCode !== old.countryCode ||
        row.labelId !== old.labelId
      );
    })
    .map((row) => row.clientKey);
  if (changed.length) emit("clearPointErrors", changed);
});
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
    phones.value = (contact?.phones ?? []).map((row) => ({ ...row }));
    emails.value = (contact?.emails ?? []).map((row) => ({ ...row }));
  },
  { immediate: true },
);

function optionalName(value: string): string | null {
  return value.trim() || null;
}

function submit() {
  attempted.value = true;
  if (
    !canSubmit.value ||
    props.pending ||
    !pointsValid.value ||
    Object.keys(validateContactPoints(phones.value, "phone")).length ||
    Object.keys(validateContactPoints(emails.value, "email")).length
  )
    return;
  emit("submit", {
    firstName: firstName.value.trim(),
    lastName: optionalName(lastName.value),
    middleName: optionalName(middleName.value),
    phones: phones.value.map((row) => ({ ...row })),
    emails: emails.value.map((row) => ({ ...row })),
  });
}
</script>

<template>
  <Dialog :open="open" @update:open="!pending && emit('update:open', $event)">
    <DialogContent
      class="max-h-[90dvh] overflow-y-auto sm:max-w-3xl"
      :show-close-button="!pending"
    >
      <form class="flex flex-col gap-4" @submit.prevent="submit" novalidate>
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
        <ContactPointsWidget
          v-model:phones="phones"
          v-model:emails="emails"
          :labels="labels"
          :pending="pending"
          :attempted="attempted"
          :errors="pointErrors"
          :labels-loading="labelsLoading"
          :labels-error="labelsError"
          @validation-change="pointsValid = $event"
          @retry="emit('retryLabels')"
        />
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
