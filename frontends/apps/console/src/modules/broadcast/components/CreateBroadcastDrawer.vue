<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import type { CreateBroadcastPayload } from "@/modules/broadcast/api";

const props = withDefaults(
  defineProps<{
    error?: string | null;
    isSubmitting?: boolean;
    open: boolean;
  }>(),
  {
    error: null,
    isSubmitting: false,
  },
);

const emit = defineEmits<{
  (event: "submit", payload: CreateBroadcastPayload): void;
  (event: "update:open", value: boolean): void;
}>();

const title = ref("");
const description = ref("");
const submitAttempted = ref(false);
const titleError = computed(() =>
  submitAttempted.value && !title.value.trim() ? "Title is required." : null,
);

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      return;
    }

    title.value = "";
    description.value = "";
    submitAttempted.value = false;
  },
);

function submit() {
  submitAttempted.value = true;

  if (titleError.value) {
    return;
  }

  emit("submit", {
    title: title.value.trim(),
    description: description.value.trim() || null,
  });
}
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent class="w-[min(34rem,100vw)] overflow-y-auto p-4 sm:max-w-xl">
      <SheetHeader class="gap-1 p-0 pr-8">
        <SheetTitle>New broadcast</SheetTitle>
        <SheetDescription>
          Create a draft broadcast record for the current tenant.
        </SheetDescription>
      </SheetHeader>

      <form class="mt-4 flex flex-1 flex-col gap-4" @submit.prevent="submit">
        <Alert v-if="error" variant="destructive">
          <AlertDescription>{{ error }}</AlertDescription>
        </Alert>

        <FieldGroup class="gap-4">
          <Field :data-invalid="!!titleError">
            <FieldLabel for="broadcast-title">Title</FieldLabel>
            <Input
              id="broadcast-title"
              v-model="title"
              :aria-invalid="!!titleError"
              :disabled="isSubmitting"
              autocomplete="off"
              placeholder="Monthly promo"
            />
            <FieldError v-if="titleError" :errors="[titleError]" />
          </Field>

          <Field>
            <FieldLabel for="broadcast-description">Description</FieldLabel>
            <Textarea
              id="broadcast-description"
              v-model="description"
              :disabled="isSubmitting"
              class="min-h-28 resize-none"
              placeholder="Internal notes"
            />
          </Field>
        </FieldGroup>

        <SheetFooter class="mt-auto flex-row justify-end gap-2 px-0">
          <Button
            type="button"
            variant="outline"
            :disabled="isSubmitting"
            @click="emit('update:open', false)"
          >
            Cancel
          </Button>
          <Button type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? "Creating..." : "Create" }}
          </Button>
        </SheetFooter>
      </form>
    </SheetContent>
  </Sheet>
</template>
