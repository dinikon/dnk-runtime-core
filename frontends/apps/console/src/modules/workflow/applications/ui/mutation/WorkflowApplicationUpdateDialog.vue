<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import type {
  WorkflowApplicationListItem,
  WorkflowApplicationMutationPayload,
} from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationMutationForm from "@/modules/workflow/applications/ui/mutation/WorkflowApplicationMutationForm.vue";

const props = defineProps<{
  open: boolean;
  saving: boolean;
  application: WorkflowApplicationListItem | null;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "submit", value: WorkflowApplicationMutationPayload): void;
}>();

const formRef = ref<InstanceType<
  typeof WorkflowApplicationMutationForm
> | null>(null);

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit("update:open", value),
});

const initialValue = computed<WorkflowApplicationMutationPayload | null>(() => {
  if (props.application === null) {
    return null;
  }

  return {
    title: props.application.title,
    description: props.application.description,
    icon: props.application.icon,
    iconBackground: props.application.iconBackground,
  };
});

const canSubmit = computed(() => {
  return formRef.value?.canSubmit ?? false;
});

function closeDialog() {
  isOpen.value = false;
}

function submitForm() {
  formRef.value?.submit();
}

watch(
  () => [props.open, props.application?.id] as const,
  () => {
    formRef.value?.reset();
  },
  {
    flush: "post",
  },
);
</script>

<template>
  <Sheet v-model:open="isOpen">
    <SheetContent class="w-[min(34rem,100vw)] gap-0 p-0 sm:max-w-xl">
      <SheetHeader class="border-b px-6 py-4 pr-12">
        <SheetTitle>Edit workflow application</SheetTitle>
        <SheetDescription>
          Update workflow app title, description, icon, and background.
        </SheetDescription>
      </SheetHeader>

      <WorkflowApplicationMutationForm
        ref="formRef"
        :disabled="saving"
        :initial-value="initialValue"
        class="min-h-0 flex-1 overflow-y-auto px-6 py-5"
        @submit="emit('submit', $event)"
      />

      <SheetFooter class="border-t px-6 py-4 sm:flex-row sm:justify-end">
        <Button
          type="button"
          variant="outline"
          :disabled="saving"
          @click="closeDialog"
        >
          Cancel
        </Button>

        <Button
          type="button"
          :disabled="!canSubmit || saving || application === null"
          @click="submitForm"
        >
          <Spinner v-if="saving" data-icon="inline-start" />
          {{ saving ? "Saving" : "Save" }}
        </Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>
