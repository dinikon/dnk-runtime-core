<script setup lang="ts">
import { ref, watch } from "vue";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { FieldGroup } from "@/components/ui/field";
import PhoneContactPointsField from "./PhoneContactPointsField.vue";
import EmailContactPointsField from "./EmailContactPointsField.vue";
import type {
  ContactPointDraft,
  ContactPointLabel,
  ContactPointErrors,
} from "../model/types";
defineProps<{
  phones: ContactPointDraft[];
  emails: ContactPointDraft[];
  labels: ContactPointLabel[];
  disabled?: boolean;
  pending?: boolean;
  attempted?: boolean;
  errors?: ContactPointErrors;
  labelsLoading?: boolean;
  labelsError?: boolean;
}>();
const emit = defineEmits<{
  "update:phones": [rows: ContactPointDraft[]];
  "update:emails": [rows: ContactPointDraft[]];
  "validation-change": [valid: boolean];
  retry: [];
}>();
const phoneValid = ref(true),
  emailValid = ref(true);
watch(
  [phoneValid, emailValid],
  ([phone, email]) => emit("validation-change", phone && email),
  { immediate: true },
);
</script>
<template>
  <FieldGroup class="min-w-0 gap-6">
    <div
      v-if="labelsLoading"
      role="status"
      class="flex items-center gap-2 text-sm text-muted-foreground"
    >
      <Spinner />Загрузка подписей…
    </div>
    <Alert v-if="labelsError" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-2"
        >Не удалось загрузить подписи.<Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="pending"
          @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <PhoneContactPointsField
      :model-value="phones"
      :labels="labels"
      :disabled="disabled"
      :pending="pending"
      :attempted="attempted"
      :errors="errors"
      :labels-loading="labelsLoading"
      :labels-error="labelsError"
      @update:model-value="emit('update:phones', $event)"
      @validation-change="phoneValid = $event"
    />
    <EmailContactPointsField
      :model-value="emails"
      :labels="labels"
      :disabled="disabled"
      :pending="pending"
      :attempted="attempted"
      :errors="errors"
      :labels-loading="labelsLoading"
      :labels-error="labelsError"
      @update:model-value="emit('update:emails', $event)"
      @validation-change="emailValid = $event"
    />
  </FieldGroup>
</template>
