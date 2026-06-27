<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Info, Plus } from "@lucide/vue";
import { toast } from "vue-sonner";

import { getApiErrorMessage } from "@/app/providers/http";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import type { WorkflowApplication } from "@/modules/workflow/api";
import { useCreateWorkflowMutation } from "@/modules/workflow/mutations/use-create-workflow";

const DEFAULT_ICON = "🚀";
const DEFAULT_ICON_BACKGROUND = "#2563EB";

const iconOptions = [
  { value: "🚀", label: "Rocket" },
  { value: "✨", label: "Sparkles" },
  { value: "⚙️", label: "Gear" },
  { value: "💬", label: "Message" },
  { value: "📣", label: "Campaign" },
  { value: "🎯", label: "Goal" },
  { value: "⚡", label: "Trigger" },
  { value: "🧩", label: "Step" },
  { value: "📦", label: "Package" },
  { value: "✅", label: "Done" },
];

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
    ? "Use a hex color like #2563EB."
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
      class="!w-full !max-w-none overflow-y-auto p-4 sm:!w-[90vw] sm:!max-w-[90vw] sm:p-6"
    >
      <SheetHeader class="p-0 pr-8">
        <SheetTitle>Create workflow</SheetTitle>
        <SheetDescription>
          Set up the basic identity for a new flow.
        </SheetDescription>
      </SheetHeader>

      <form class="flex flex-1 flex-col gap-5" @submit.prevent="createWorkflow">
        <Alert>
          <Info aria-hidden="true" />
          <AlertTitle>What is a workflow?</AlertTitle>
          <AlertDescription>
            A workflow is an automated flow of steps that reacts to events and
            moves work through a repeatable process.
          </AlertDescription>
        </Alert>

        <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <FieldGroup>
            <Field :data-invalid="Boolean(titleError)">
              <FieldLabel for="workflow-title">Name</FieldLabel>
              <Input
                id="workflow-title"
                v-model="title"
                :aria-invalid="Boolean(titleError)"
                placeholder="Welcome journey"
              />
              <FieldError v-if="titleError">{{ titleError }}</FieldError>
            </Field>

            <Field>
              <FieldLabel for="workflow-description">
                Description
              </FieldLabel>
              <Textarea
                id="workflow-description"
                v-model="description"
                class="min-h-28 resize-none"
                placeholder="Optional context for the team"
              />
              <FieldDescription>
                Keep it short. You can refine the flow itself later.
              </FieldDescription>
            </Field>

            <div class="grid gap-4 md:grid-cols-2">
              <Field>
                <FieldLabel for="workflow-icon">Icon</FieldLabel>
                <Select v-model="icon">
                  <SelectTrigger id="workflow-icon" class="w-full">
                    <SelectValue placeholder="Choose icon" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem
                        v-for="option in iconOptions"
                        :key="option.value"
                        :value="option.value"
                      >
                        <span>{{ option.value }}</span>
                        <span>{{ option.label }}</span>
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>

              <Field :data-invalid="Boolean(iconBackgroundError)">
                <FieldLabel for="workflow-icon-background">
                  Icon background
                </FieldLabel>
                <div class="grid gap-2 sm:grid-cols-[3.25rem_minmax(0,1fr)]">
                  <Input
                    id="workflow-icon-background-picker"
                    v-model="iconBackground"
                    aria-label="Choose icon background"
                    class="h-10 p-1"
                    type="color"
                  />
                  <Input
                    id="workflow-icon-background"
                    v-model="iconBackground"
                    :aria-invalid="Boolean(iconBackgroundError)"
                    placeholder="#2563EB"
                  />
                </div>
                <FieldError v-if="iconBackgroundError">
                  {{ iconBackgroundError }}
                </FieldError>
              </Field>
            </div>
          </FieldGroup>

          <div class="rounded-lg border bg-muted/30 p-4">
            <div class="flex items-center gap-3">
              <div
                class="flex size-12 shrink-0 items-center justify-center rounded-md text-2xl shadow-xs"
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

        <SheetFooter class="gap-2 p-0 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            @click="sheetOpen = false"
          >
            Cancel
          </Button>
          <Button type="submit" :disabled="createWorkflowMutation.isPending.value">
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
