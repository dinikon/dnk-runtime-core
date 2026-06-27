<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Info, Plus } from "@lucide/vue";
import { toast } from "vue-sonner";

import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import EmojiPicker from "@/modules/workflow/components/EmojiPicker.vue";
import type { WorkflowApplication } from "@/modules/workflow/api";
import { useCreateWorkflowMutation } from "@/modules/workflow/mutations/use-create-workflow";

const DEFAULT_ICON = "🚀";
const DEFAULT_ICON_BACKGROUND = "#FDEAD7";

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "created", workflow: WorkflowApplication): void;
}>();

const createWorkflowMutation = useCreateWorkflowMutation();

const title = ref("");
const description = ref("");
const icon = ref(DEFAULT_ICON);
const iconBackground = ref(DEFAULT_ICON_BACKGROUND);
const submitted = ref(false);

const sheetOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit("update:open", value),
});

const titleError = computed(() =>
  submitted.value && title.value.trim().length === 0
    ? "Workflow name is required."
    : "",
);
const iconBackgroundError = computed(() =>
  submitted.value && !/^#[0-9A-Fa-f]{6}$/.test(iconBackground.value.trim())
    ? "Use a hex color like #FDEAD7."
    : "",
);
const previewBackground = computed(() =>
  /^#[0-9A-Fa-f]{6}$/.test(iconBackground.value.trim())
    ? iconBackground.value.trim()
    : DEFAULT_ICON_BACKGROUND,
);

function resetForm() {
  title.value = "";
  description.value = "";
  icon.value = DEFAULT_ICON;
  iconBackground.value = DEFAULT_ICON_BACKGROUND;
  submitted.value = false;
}

async function createWorkflow() {
  submitted.value = true;

  if (titleError.value || iconBackgroundError.value) {
    return;
  }

  try {
    const workflow = await createWorkflowMutation.mutateAsync({
      title: title.value.trim(),
      description: description.value.trim() || null,
      icon: icon.value,
      icon_background: iconBackground.value.trim(),
    });

    toast.success(`${workflow.title} created.`);
    emit("created", workflow);
    sheetOpen.value = false;
    resetForm();
  } catch (error) {
    toast.error(getApiErrorMessage(error, "Workflow was not created."));
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      resetForm();
    }
  },
);
</script>

<template>
  <Sheet v-model:open="sheetOpen">
    <SheetContent
      class="w-full! max-w-none! gap-0 overflow-hidden p-0 sm:w-[min(44rem,92vw)]! sm:max-w-176!"
    >
      <SheetHeader class="border-b px-5 py-4 pr-14 text-left">
        <SheetTitle>Create workflow</SheetTitle>
        <SheetDescription>
          Name the flow and choose how it appears in the list.
        </SheetDescription>
      </SheetHeader>

      <form
        class="flex min-h-0 flex-1 flex-col"
        @submit.prevent="createWorkflow"
      >
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <div class="mx-auto flex w-full max-w-160 flex-col gap-5">
            <Alert class="rounded-xl py-3">
              <Info aria-hidden="true" />
              <AlertTitle>What is a workflow?</AlertTitle>
              <AlertDescription>
                An automated sequence of steps that reacts to events and moves
                work through a repeatable process.
              </AlertDescription>
            </Alert>

            <FieldGroup class="gap-5">
              <Field :data-invalid="Boolean(titleError || iconBackgroundError)">
                <div
                  class="grid grid-cols-[minmax(0,1fr)_5.625rem] items-stretch gap-3"
                >
                  <div class="flex min-w-0 flex-col gap-3">
                    <FieldLabel
                      for="workflow-title"
                      class="text-base font-semibold"
                    >
                      App Name &amp; Icon
                    </FieldLabel>
                    <Input
                      id="workflow-title"
                      v-model="title"
                      :aria-invalid="Boolean(titleError)"
                      class="h-14 rounded-2xl bg-muted/60 px-5 text-base shadow-none"
                      placeholder="Give your workflow a name"
                    />
                  </div>
                  <EmojiPicker
                    v-model="icon"
                    v-model:background="iconBackground"
                    :invalid="Boolean(iconBackgroundError)"
                    trigger-class="h-full min-h-[5.625rem] w-full"
                    icon-class="text-4xl"
                  />
                </div>
                <FieldError v-if="titleError">{{ titleError }}</FieldError>
                <FieldError v-if="iconBackgroundError">
                  {{ iconBackgroundError }}
                </FieldError>
              </Field>

              <Field>
                <div class="flex items-baseline gap-2">
                  <FieldLabel
                    for="workflow-description"
                    class="text-base font-semibold"
                  >
                    Description
                  </FieldLabel>
                  <span class="text-sm text-muted-foreground">(Optional)</span>
                </div>
                <Textarea
                  id="workflow-description"
                  v-model="description"
                  class="min-h-32 resize-none rounded-2xl bg-muted/60 px-5 py-4 text-base shadow-none"
                  placeholder="Enter the description of the workflow"
                />
              </Field>
            </FieldGroup>

            <div class="rounded-xl border bg-card p-3">
              <div class="flex items-center gap-3">
                <div
                  class="flex size-12 shrink-0 items-center justify-center rounded-xl text-2xl shadow-xs"
                  :style="{ backgroundColor: previewBackground }"
                  aria-hidden="true"
                >
                  {{ icon }}
                </div>
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium">
                    {{ title.trim() || "New workflow" }}
                  </p>
                  <p class="truncate text-sm text-muted-foreground">
                    {{ description.trim() || "Draft flow" }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <SheetFooter
          class="gap-2 border-t bg-background px-5 py-4 sm:flex-row sm:justify-end"
        >
          <Button type="button" variant="outline" @click="sheetOpen = false">
            Cancel
          </Button>
          <Button
            type="submit"
            :disabled="createWorkflowMutation.isPending.value"
          >
            <Spinner
              v-if="createWorkflowMutation.isPending.value"
              data-icon="inline-start"
            />
            <Plus v-else data-icon="inline-start" />
            {{ createWorkflowMutation.isPending.value ? "Creating" : "Create" }}
          </Button>
        </SheetFooter>
      </form>
    </SheetContent>
  </Sheet>
</template>
