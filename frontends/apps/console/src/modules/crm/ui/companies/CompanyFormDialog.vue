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
import type { Company, CompanyInput } from "../../model/crm.types";

const props = defineProps<{
  open: boolean;
  company: Company | null;
  pending: boolean;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  submit: [input: CompanyInput];
}>();

const name = ref("");
const attempted = ref(false);
const canSubmit = computed(
  () => name.value.trim().length > 0 && name.value.trim().length <= 255,
);

watch(
  () => [props.open, props.company] as const,
  ([open, company]) => {
    if (!open) return;
    name.value = company?.name ?? "";
    attempted.value = false;
  },
  { immediate: true },
);

function submit() {
  attempted.value = true;
  if (!canSubmit.value || props.pending) return;
  emit("submit", { name: name.value.trim() });
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent>
      <form class="flex flex-col gap-4" @submit.prevent="submit">
        <DialogHeader>
          <DialogTitle>{{
            company ? "Редактировать компанию" : "Новая компания"
          }}</DialogTitle>
          <DialogDescription>
            Укажите отображаемое название компании.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field :data-invalid="attempted && !canSubmit ? true : undefined">
            <FieldLabel for="company-name">Название</FieldLabel>
            <Input
              id="company-name"
              v-model="name"
              maxlength="255"
              autocomplete="organization"
              required
              :aria-invalid="attempted && !canSubmit"
              :disabled="pending"
            />
            <FieldError v-if="attempted && !canSubmit">
              Название обязательно и должно быть не длиннее 255 символов.
            </FieldError>
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
            {{ company ? "Сохранить" : "Создать" }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
