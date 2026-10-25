<script setup lang="ts">
import { validateContactPoints } from "@/modules/contact-points";
import { ref, watch } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import SaleFields from "./SaleFields.vue";
import SalePointsEditor from "./SalePointsEditor.vue";
import type { SaleDraft, SalesKind } from "../../model/sales.types";
import type { Funnel } from "@/modules/funnel";
import type { ContactPointLabel } from "@/modules/contact-points";
import { validateSaleDraft } from "../../model/sales.draft";
const props = defineProps<{
  open: boolean;
  kind: SalesKind;
  modelValue: SaleDraft;
  funnels: Funnel[];
  contacts: { id: string; label: string }[];
  companies: { id: string; label: string }[];
  labels: ContactPointLabel[];
  pending: boolean;
  error: string;
  labelsError?: boolean;
  labelsLoading?: boolean;
  peopleLoading?: boolean;
  peopleError?: boolean;
  contactPreview?: { name: string; values: string[] };
  previewLoading?: boolean;
  previewError?: boolean;
}>();
const emit = defineEmits<{
  "update:open": [open: boolean];
  "update:modelValue": [value: SaleDraft];
  submit: [];
  copyContact: [id: string];
  close: [];
  retryPeople: [];
}>();
const localError = ref("");
watch(
  () => props.open,
  () => (localError.value = ""),
);
function submit() {
  if (props.pending) return;
  localError.value = validateSaleDraft(props.modelValue) ?? "";
  if (
    !localError.value &&
    ["phone", "email"].some(
      (kind) =>
        Object.keys(
          validateContactPoints(
            kind === "phone"
              ? props.modelValue.points.phones
              : props.modelValue.points.emails,
            kind as "phone" | "email",
          ),
        ).length,
    )
  )
    localError.value = "Проверьте телефоны и email.";
  if (!localError.value) emit("submit");
}
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')"
    ><DialogContent
      class="max-h-[90dvh] overflow-y-auto sm:max-w-2xl"
      :show-close-button="!pending"
      @interact-outside="pending && $event.preventDefault()"
      @escape-key-down="pending && $event.preventDefault()"
      ><form class="flex flex-col gap-5" @submit.prevent="submit">
        <DialogHeader
          ><DialogTitle>{{
            kind === "leads" ? "Новый лид" : "Новая сделка"
          }}</DialogTitle
          ><DialogDescription
            >Создайте карточку. Товары и услуги можно добавить после
            открытия.</DialogDescription
          ></DialogHeader
        ><Alert v-if="error || localError" variant="destructive"
          ><AlertDescription role="alert">{{
            error || localError
          }}</AlertDescription></Alert
        >
        <p
          v-if="peopleLoading"
          role="status"
          class="text-sm text-muted-foreground"
        >
          Загружаем контакты и компании…
        </p>
        <Alert v-if="peopleError" variant="destructive"
          ><AlertDescription
            >Не удалось загрузить контакты и компании.
            <Button type="button" variant="outline" @click="emit('retryPeople')"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        ><SaleFields
          :kind="kind"
          :contact-preview="contactPreview"
          :preview-loading="previewLoading"
          :preview-error="previewError"
          :model-value="modelValue"
          :funnels="funnels"
          :contacts="contacts"
          :companies="companies"
          creating
          :disabled="pending"
          @update:model-value="emit('update:modelValue', $event)"
          @copy-contact="emit('copyContact', $event)"
        /><SalePointsEditor
          v-if="kind === 'leads'"
          :model-value="modelValue.points"
          :labels="labels"
          :disabled="pending"
          :loading="labelsLoading"
          :error="labelsError"
          @update:model-value="
            emit('update:modelValue', { ...modelValue, points: $event })
          "
        /><DialogFooter
          ><Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('close')"
            >Отмена</Button
          ><Button type="submit" :disabled="pending">{{
            pending ? "Создаём…" : "Создать и открыть"
          }}</Button></DialogFooter
        >
      </form></DialogContent
    ></Dialog
  >
</template>
