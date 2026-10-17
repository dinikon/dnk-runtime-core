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
import type { CompanyInput } from "../../model/crm.types";

const props = defineProps<{ open: boolean; pending: boolean }>();
const emit = defineEmits<{
  "update:open": [open: boolean];
  submit: [input: CompanyInput];
}>();
const legalName = ref("");
const attempted = ref(false);
watch(
  () => props.open,
  (open) => {
    if (!open) return;
    legalName.value = "";
    attempted.value = false;
  },
);
function submit() {
  attempted.value = true;
  const name = legalName.value.trim();
  if (!name || name.length > 255 || props.pending) return;
  emit("submit", { legalName: name });
}
</script>

<template>
  <Dialog :open="open" @update:open="!pending && emit('update:open', $event)">
    <DialogContent
      ><form class="flex flex-col gap-4" @submit.prevent="submit">
        <DialogHeader
          ><DialogTitle>Новая компания</DialogTitle>
          <DialogDescription
            >Сначала создайте компанию. Связи и контактные данные можно добавить
            на её странице.</DialogDescription
          >
        </DialogHeader>
        <FieldGroup
          ><Field
            :data-invalid="attempted && !legalName.trim() ? true : undefined"
          >
            <FieldLabel for="new-company-name">Название</FieldLabel>
            <Input
              id="new-company-name"
              v-model="legalName"
              maxlength="255"
              required
              :aria-invalid="attempted && !legalName.trim()"
              :disabled="pending"
            />
            <FieldError v-if="attempted && !legalName.trim()"
              >Укажите название.</FieldError
            >
          </Field></FieldGroup
        >
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
