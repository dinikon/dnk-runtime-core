<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { X } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import type { CreateWorkflowApplicationPayload } from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationMutationForm from "@/modules/workflow/applications/ui/mutation/WorkflowApplicationMutationForm.vue";

const props = defineProps<{
  open: boolean;
  saving: boolean;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "submit", value: CreateWorkflowApplicationPayload): void;
}>();

const formRef = ref<InstanceType<
  typeof WorkflowApplicationMutationForm
> | null>(null);

const isOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit("update:open", value),
});

const canSubmit = computed(() => {
  return formRef.value?.canSubmit ?? false;
});

function submitForm() {
  formRef.value?.submit();
}

watch(
  () => props.open,
  () => {
    formRef.value?.reset();
  },
);
</script>

<template>
  <Sheet v-model:open="isOpen">
    <SheetContent
      class="w-[min(34rem,100vw)] gap-0 p-0 sm:max-w-xl"
      :show-close-button="false"
    >
      <SheetHeader
        class="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-4 gap-y-1 border-b px-6 py-4"
      >
        <div class="min-w-0">
          <SheetTitle>Create workflow application</SheetTitle>
          <SheetDescription>
            Create a workflow app with an initial empty draft definition.
          </SheetDescription>
        </div>

        <SheetClose as-child>
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            aria-label="Close"
          >
            <X data-icon="inline-start" />
            <span class="sr-only">Close</span>
          </Button>
        </SheetClose>
      </SheetHeader>

      <WorkflowApplicationMutationForm
        ref="formRef"
        :disabled="saving"
        class="min-h-0 flex-1 overflow-y-auto px-6 py-5"
        @submit="emit('submit', $event)"
      />

      <SheetFooter class="border-t px-6 py-4 sm:flex-row sm:justify-end">
        <Button
          type="button"
          :disabled="!canSubmit || saving"
          @click="submitForm"
        >
          <Spinner v-if="saving" data-icon="inline-start" />
          {{ saving ? "Creating" : "Create" }}
        </Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>
