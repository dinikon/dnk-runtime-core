<script setup lang="ts">
import { computed, ref } from "vue";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  DEFAULT_EMOJI,
  DEFAULT_EMOJI_BACKGROUND,
  EmojiBackgroundPicker,
} from "@/shared/emoji-background-picker";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import type { WorkflowApplicationMutationPayload } from "@/modules/workflow/applications/model/workflow-application.types.ts";

const props = defineProps<{
  disabled?: boolean;
  initialValue?: WorkflowApplicationMutationPayload | null;
  class?: string;
}>();

const emit = defineEmits<{
  (event: "submit", value: WorkflowApplicationMutationPayload): void;
}>();

const title = ref(props.initialValue?.title ?? "");
const description = ref(props.initialValue?.description ?? "");
const icon = ref(props.initialValue?.icon ?? DEFAULT_EMOJI);
const iconBackground = ref(
  props.initialValue?.iconBackground ?? DEFAULT_EMOJI_BACKGROUND,
);
const submitAttempted = ref(false);

const trimmedTitle = computed(() => title.value.trim());
const trimmedDescription = computed(() => description.value.trim());
const titleError = computed(() => {
  if (!submitAttempted.value || trimmedTitle.value.length > 0) {
    return null;
  }

  return "Title is required.";
});
const canSubmit = computed(() => trimmedTitle.value.length > 0);

function reset() {
  title.value = props.initialValue?.title ?? "";
  description.value = props.initialValue?.description ?? "";
  icon.value = props.initialValue?.icon ?? DEFAULT_EMOJI;
  iconBackground.value =
    props.initialValue?.iconBackground ?? DEFAULT_EMOJI_BACKGROUND;
  submitAttempted.value = false;
}

function submit() {
  submitAttempted.value = true;

  if (!canSubmit.value) {
    return;
  }

  emit("submit", {
    title: trimmedTitle.value,
    description:
      trimmedDescription.value.length > 0 ? trimmedDescription.value : null,
    icon: icon.value,
    iconBackground: iconBackground.value,
  });
}

defineExpose({
  canSubmit,
  reset,
  submit,
});
</script>

<template>
  <form :class="props.class" @submit.prevent="submit">
    <FieldGroup>
      <div class="grid grid-cols-[minmax(0,1fr)_4.25rem] items-start gap-4">
        <Field :data-invalid="Boolean(titleError)">
          <FieldLabel for="workflow-application-title"> Title </FieldLabel>
          <Input
            id="workflow-application-title"
            v-model="title"
            :aria-invalid="Boolean(titleError)"
            :disabled="disabled"
            placeholder="Customer onboarding"
            required
          />
          <FieldError v-if="titleError">
            {{ titleError }}
          </FieldError>
        </Field>

        <Field class="w-17">
          <FieldLabel class="sr-only"> Icon and background color </FieldLabel>
          <EmojiBackgroundPicker
            v-model="icon"
            v-model:background="iconBackground"
            :disabled="disabled"
            trigger-class="size-[4.25rem] rounded-xl"
            emoji-class="rounded-lg text-3xl"
            title="Workflow app icon"
            description="Choose an icon and background color for the workflow app card."
          />
        </Field>
      </div>

      <Field>
        <FieldLabel for="workflow-application-description">
          Description
        </FieldLabel>
        <Textarea
          id="workflow-application-description"
          v-model="description"
          :disabled="disabled"
          class="min-h-28"
          placeholder="Optional workflow app description"
        />
      </Field>
    </FieldGroup>
  </form>
</template>
