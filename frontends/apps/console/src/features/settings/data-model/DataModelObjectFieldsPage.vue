<script setup lang="ts">
import {computed, onMounted, reactive, ref, watch} from "vue";
import {RouterLink, useRoute, useRouter} from "vue-router";
import {
  Database,
  ExternalLink,
  Loader2,
  Plus,
  Search,
  Settings,
  Shield,
  Trash2,
} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {
  schemaRegistryApi,
  type CustomFieldInput,
  type FieldType,
  type RuntimeField,
  type RuntimeObject
} from "@/api/schema-registry";
import {Alert, AlertDescription} from "@/components/ui/alert";
import {Button} from "@/components/ui/button";
import {Checkbox} from "@/components/ui/checkbox";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle
} from "@/components/ui/sheet";
import {Textarea} from "@/components/ui/textarea";
import {SettingsLayout} from "@/layouts";

interface OptionRow {
  value: string;
  label: string;
}

const IDENTIFIER_PATTERN = /^[a-z][a-z0-9_]*$/;
const FIELD_TYPES: FieldType[] = [
  "text",
  "int",
  "decimal",
  "bool",
  "date",
  "datetime",
  "json",
  "uuid",
  "select",
  "multiselect"
];

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();

const object = ref<RuntimeObject | null>(null);
const isLoading = ref(false);
const isCreatingField = ref(false);
const isDeletingObject = ref(false);
const deletingFieldId = ref<string | null>(null);
const pageError = ref<string | null>(null);
const createFieldErrors = ref<string[]>([]);
const searchQuery = ref("");
const isCreateFieldDialogOpen = ref(false);
const fieldForm = reactive({
  label: "",
  field_name: "",
  type: "text" as FieldType,
  description: "",
  default_value: "",
  is_required: false
});
const optionRows = ref<OptionRow[]>([]);

const objectId = computed(() => {
  const rawObjectId = route.params.objectId;
  return Array.isArray(rawObjectId) ? rawObjectId[0] : rawObjectId;
});
const fields = computed(() => object.value?.fields ?? []);
const filteredFields = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();

  if (!query) {
    return fields.value;
  }

  return fields.value.filter((field) => (
      field.label.toLowerCase().includes(query) ||
      field.field_name.toLowerCase().includes(query) ||
      field.type.toLowerCase().includes(query)
  ));
});
const canManageFields = computed(() => {
  const kind = object.value?.kind.trim().toLowerCase();
  return kind === "standard" || kind === "custom";
});
const canDeleteCurrentObject = computed(() => object.value?.kind.trim().toLowerCase() === "custom");
const isSelectLikeField = computed(() => isSelectLikeFieldType(fieldForm.type));

onMounted(() => {
  void loadObject();
});

watch(objectId, () => {
  void loadObject();
});

async function loadObject() {
  if (!objectId.value) {
    await router.replace({
      path: "/settings/workspace/data-model",
      query: {error: "object-not-found"}
    });
    return;
  }

  isLoading.value = true;
  pageError.value = null;

  try {
    object.value = await schemaRegistryApi.describeObject(objectId.value);
  } catch (error) {
    if (getApiErrorStatus(error) === 404) {
      await router.replace({
        path: "/settings/workspace/data-model",
        query: {error: "object-not-found"}
      });
      return;
    }

    await handleApiFailure(error, "Could not load object schema.");
  } finally {
    isLoading.value = false;
  }
}

function openCreateFieldDialog() {
  resetFieldForm();
  isCreateFieldDialogOpen.value = true;
}

function closeCreateFieldDialog() {
  if (isCreatingField.value) {
    return;
  }

  isCreateFieldDialogOpen.value = false;
}

function handleCreateFieldSheetOpen(open: boolean) {
  if (open) {
    openCreateFieldDialog();
    return;
  }

  closeCreateFieldDialog();
}

function handleFieldTypeChange(value: unknown) {
  if (typeof value !== "string" || !FIELD_TYPES.includes(value as FieldType)) {
    return;
  }

  fieldForm.type = value as FieldType;
}

async function submitCreateField() {
  if (!object.value || !canManageFields.value) {
    return;
  }

  const errors = validateFieldForm();
  createFieldErrors.value = errors;

  if (errors.length > 0) {
    return;
  }

  isCreatingField.value = true;

  try {
    object.value = await schemaRegistryApi.createField(object.value.id, buildFieldPayload());
    isCreateFieldDialogOpen.value = false;
  } catch (error) {
    if (getApiErrorStatus(error) === 404) {
      await router.replace({
        path: "/settings/workspace/data-model",
        query: {error: "object-not-found"}
      });
      return;
    }

    if (getApiErrorStatus(error) === 401) {
      sessionStore.clearSession();
      await router.push("/login");
      return;
    }

    createFieldErrors.value = [getApiErrorMessage(error, "Could not create field.")];
  } finally {
    isCreatingField.value = false;
  }
}

async function deleteField(field: RuntimeField) {
  if (!object.value || !canDeleteField(field) || deletingFieldId.value) {
    return;
  }

  const confirmed = window.confirm(`Delete ${field.label}? This will permanently remove the field column.`);
  if (!confirmed) {
    return;
  }

  deletingFieldId.value = field.id;
  pageError.value = null;

  try {
    object.value = await schemaRegistryApi.deleteField(object.value.id, field.id);
  } catch (error) {
    if (getApiErrorStatus(error) === 404) {
      await router.replace({
        path: "/settings/workspace/data-model",
        query: {error: "object-not-found"}
      });
      return;
    }

    await handleApiFailure(error, "Could not delete field.");
  } finally {
    deletingFieldId.value = null;
  }
}

async function deleteCurrentObject() {
  if (!object.value || !canDeleteCurrentObject.value || isDeletingObject.value) {
    return;
  }

  const confirmed = window.confirm(`Delete ${object.value.plural_label}? This will permanently remove the object table.`);
  if (!confirmed) {
    return;
  }

  isDeletingObject.value = true;
  pageError.value = null;

  try {
    await schemaRegistryApi.deleteObject(object.value.id);
    await router.push("/settings/workspace/data-model");
  } catch (error) {
    await handleApiFailure(error, "Could not delete object.");
  } finally {
    isDeletingObject.value = false;
  }
}

function addOptionRow() {
  optionRows.value.push({
    value: "",
    label: ""
  });
}

function removeOptionRow(index: number) {
  optionRows.value.splice(index, 1);
}

function resetFieldForm() {
  fieldForm.label = "";
  fieldForm.field_name = "";
  fieldForm.type = "text";
  fieldForm.description = "";
  fieldForm.default_value = "";
  fieldForm.is_required = false;
  optionRows.value = [];
  createFieldErrors.value = [];
}

function validateFieldForm(): string[] {
  const errors: string[] = [];
  const label = fieldForm.label.trim();
  const fieldName = fieldForm.field_name.trim();
  const defaultValue = fieldForm.default_value.trim();

  validateLabel(label, "Field label", errors);
  validateIdentifier(fieldName, "Field identifier", errors);

  if (fieldForm.is_required && !defaultValue) {
    errors.push("Required field must have a default value.");
  }

  if (isSelectLikeField.value) {
    validateOptionRows(errors);
  }

  return errors;
}

function validateLabel(value: string, label: string, errors: string[]) {
  if (!value) {
    errors.push(`${label} is required.`);
    return;
  }

  if (value.length > 32) {
    errors.push(`${label} must be 32 characters or fewer.`);
  }
}

function validateIdentifier(value: string, label: string, errors: string[]) {
  if (!value) {
    errors.push(`${label} is required.`);
    return;
  }

  if (value.length > 63) {
    errors.push(`${label} must be 63 characters or fewer.`);
  }

  if (!IDENTIFIER_PATTERN.test(value)) {
    errors.push(`${label} must match ^[a-z][a-z0-9_]*$.`);
  }
}

function validateOptionRows(errors: string[]) {
  const seenValues = new Set<string>();

  optionRows.value.forEach((row, index) => {
    const value = row.value.trim();
    const label = row.label.trim();

    if (!value && !label) {
      return;
    }

    if (!value || !label) {
      errors.push(`Option ${index + 1} must have value and label.`);
      return;
    }

    if (seenValues.has(value)) {
      errors.push(`Option value ${value} is duplicated.`);
      return;
    }

    seenValues.add(value);
  });
}

function buildFieldPayload(): CustomFieldInput {
  return {
    label: fieldForm.label.trim(),
    field_name: fieldForm.field_name.trim(),
    type: fieldForm.type,
    description: fieldForm.description.trim(),
    is_nullable: !fieldForm.is_required,
    default_value: normalizeOptionalText(fieldForm.default_value),
    options: isSelectLikeField.value ? buildOptionsPayload() : {},
    settings: {}
  };
}

function buildOptionsPayload(): Record<string, string> {
  return optionRows.value.reduce<Record<string, string>>((result, row) => {
    const value = row.value.trim();
    const label = row.label.trim();

    if (value && label) {
      result[value] = label;
    }

    return result;
  }, {});
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function canDeleteField(field: RuntimeField): boolean {
  return field.kind.trim().toLowerCase() === "custom";
}

function kindLabel(kind: string): string {
  return kind.trim().toLowerCase() === "custom" ? "Custom" : "Standard";
}

function fieldKindLabel(kind: string): string {
  return kind.trim().toLowerCase() === "custom" ? "Custom" : "Standard";
}

function kindClass(kind: string): string {
  return kind.trim().toLowerCase() === "custom"
      ? "bg-secondary text-secondary-foreground ring-border"
      : "bg-muted text-muted-foreground ring-border";
}

function fieldTypeLabel(type: string): string {
  if (type === "uuid") {
    return "UUID";
  }

  return type
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
}

function isSelectLikeFieldType(type: string): boolean {
  return type === "select" || type === "multiselect";
}

async function handleApiFailure(error: unknown, fallback: string) {
  if (getApiErrorStatus(error) === 401) {
    sessionStore.clearSession();
    await router.push("/login");
    return;
  }

  pageError.value = getApiErrorMessage(error, fallback);
}
</script>

<template>
  <SettingsLayout
      :title="object?.plural_label ?? 'Data Model'"
      active-item="data-model"
      :breadcrumbs="[
      {label: 'Workspace'},
      {label: 'Data Model', to: '/settings/workspace/data-model'},
      {label: object?.plural_label ?? 'Object'}
    ]"
  >
    <div class="flex min-h-[560px] flex-col">
      <div v-if="isLoading" class="grid flex-1 place-items-center text-sm text-muted-foreground">
        <span class="inline-flex items-center gap-2">
          <Loader2 class="size-4 animate-spin"/>
          Loading object...
        </span>
      </div>

      <div v-else-if="object" class="flex flex-1 flex-col">
        <header class="flex items-start justify-between gap-4">
          <div class="flex min-w-0 items-center gap-3">
            <span class="grid size-7 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground">
              <Database class="size-4"/>
            </span>
            <div class="min-w-0">
              <div class="flex min-w-0 items-center gap-2">
                <h1 class="truncate text-base font-semibold">{{ object.plural_label }}</h1>
                <span
                    class="inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1"
                    :class="kindClass(object.kind)"
                >
                  {{ kindLabel(object.kind) }}
                </span>
              </div>
              <p class="mt-1 truncate text-sm text-muted-foreground">{{ object.description || object.plural_name }}</p>
            </div>
          </div>

          <div class="flex shrink-0 items-center gap-2">
            <Button as-child variant="outline" size="sm">
              <RouterLink :to="{path: '/', query: {object: object.id}}">
                <ExternalLink class="size-4"/>
                See records
              </RouterLink>
            </Button>
            <Button
                v-if="canDeleteCurrentObject"
                type="button"
                variant="destructive"
                size="sm"
                :disabled="isDeletingObject"
                @click="deleteCurrentObject"
            >
              <Loader2 v-if="isDeletingObject" class="size-4 animate-spin"/>
              <Trash2 v-else class="size-4"/>
              Delete
            </Button>
            <Button
                type="button"
                size="sm"
                :disabled="!canManageFields"
                @click="openCreateFieldDialog"
            >
              <Plus class="size-4"/>
              New Field
            </Button>
          </div>
        </header>

        <Alert v-if="pageError" class="mt-5" variant="destructive">
          <AlertDescription>{{ pageError }}</AlertDescription>
        </Alert>

        <nav class="mt-8 flex items-center gap-2 border-b">
          <Button class="-mb-px rounded-none border-b-2 border-foreground px-0" variant="ghost" type="button">
            <Database class="size-4"/>
            Fields
          </Button>
          <Button variant="ghost" type="button" disabled>
            <Shield class="size-4"/>
            Permissions
          </Button>
          <Button variant="ghost" type="button" disabled>
            <Settings class="size-4"/>
            Settings
          </Button>
        </nav>

        <section class="mt-7 grid gap-5">
          <div class="grid gap-1">
            <h2 class="text-sm font-semibold">Fields</h2>
            <p class="text-sm text-muted-foreground">Customize fields available in object views and records</p>
          </div>

          <div class="relative max-w-3xl">
            <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"/>
            <Input v-model="searchQuery" class="pl-9" placeholder="Search a field..."/>
          </div>

          <div class="max-w-5xl overflow-hidden rounded-md border">
            <table class="w-full border-collapse text-left text-sm">
              <thead class="bg-background text-xs font-semibold text-muted-foreground">
              <tr class="border-b">
                <th class="px-3 py-2">Name</th>
                <th class="px-3 py-2">Identifier</th>
                <th class="px-3 py-2">Data type</th>
                <th class="w-28 px-3 py-2">Required</th>
                <th class="w-16 px-3 py-2"/>
              </tr>
              </thead>
              <tbody>
              <tr v-if="filteredFields.length === 0">
                <td class="px-3 py-10 text-center text-muted-foreground" colspan="5">No fields found.</td>
              </tr>
              <tr
                  v-for="field in filteredFields"
                  v-else
                  :key="field.id"
                  class="h-11 border-b text-foreground last:border-b-0"
              >
                <td class="px-3 py-2">
                  <div class="flex min-w-0 items-center gap-2">
                    <span class="truncate font-medium">{{ field.label }}</span>
                    <span
                        class="inline-flex shrink-0 items-center rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground"
                    >
                      {{ fieldKindLabel(field.kind) }}
                    </span>
                  </div>
                </td>
                <td class="px-3 py-2">
                  <code class="text-xs text-muted-foreground">{{ field.field_name }}</code>
                </td>
                <td class="px-3 py-2">
                  <span class="rounded bg-secondary px-1.5 py-0.5 text-xs font-medium text-secondary-foreground">
                    {{ fieldTypeLabel(field.type) }}
                  </span>
                </td>
                <td class="px-3 py-2 text-muted-foreground">{{ field.is_nullable ? "Optional" : "Required" }}</td>
                <td class="px-3 py-2">
                  <Button
                      v-if="canDeleteField(field)"
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      :disabled="deletingFieldId === field.id"
                      @click="deleteField(field)"
                  >
                    <Loader2 v-if="deletingFieldId === field.id" class="size-4 animate-spin"/>
                    <Trash2 v-else class="size-4"/>
                  </Button>
                </td>
              </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div v-else class="grid flex-1 place-items-center text-sm text-muted-foreground">
        Object is not available.
      </div>
    </div>

    <Sheet :open="isCreateFieldDialogOpen" @update:open="handleCreateFieldSheetOpen">
      <SheetContent class="w-full overflow-y-auto sm:max-w-2xl">
        <form class="flex min-h-full flex-col" @submit.prevent="submitCreateField">
          <SheetHeader>
            <SheetTitle>New Field</SheetTitle>
            <SheetDescription>{{ object?.plural_label }}</SheetDescription>
          </SheetHeader>

          <div class="grid gap-5 px-4">
            <Alert v-if="createFieldErrors.length > 0" variant="destructive">
              <AlertDescription class="grid gap-1">
                <span v-for="error in createFieldErrors" :key="error">{{ error }}</span>
              </AlertDescription>
            </Alert>

            <div class="grid gap-4 md:grid-cols-2">
              <div class="grid gap-2">
                <Label for="field-label">Label</Label>
                <Input id="field-label" v-model="fieldForm.label" placeholder="Status"/>
              </div>
              <div class="grid gap-2">
                <Label for="field-name">Identifier</Label>
                <Input id="field-name" v-model="fieldForm.field_name" placeholder="status"/>
              </div>
              <div class="grid gap-2">
                <Label>Data type</Label>
                <Select :model-value="fieldForm.type" @update:model-value="handleFieldTypeChange">
                  <SelectTrigger class="w-full">
                    <SelectValue placeholder="Select data type"/>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="type in FIELD_TYPES" :key="type" :value="type">
                      {{ fieldTypeLabel(type) }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="grid gap-2">
                <Label for="field-default-value">Default value</Label>
                <Input id="field-default-value" v-model="fieldForm.default_value" placeholder="Optional"/>
              </div>
            </div>

            <Label class="flex items-center gap-2">
              <Checkbox v-model="fieldForm.is_required"/>
              Required
            </Label>

            <div class="grid gap-2">
              <Label for="field-description">Description</Label>
              <Textarea id="field-description" v-model="fieldForm.description" placeholder="Optional"/>
            </div>

            <section v-if="isSelectLikeField" class="grid gap-3 rounded-md border p-3">
              <div class="flex items-center justify-between gap-3">
                <h3 class="text-sm font-semibold">Options</h3>
                <Button type="button" variant="outline" size="sm" @click="addOptionRow">
                  <Plus class="size-4"/>
                  Add option
                </Button>
              </div>
              <div
                  v-for="(row, index) in optionRows"
                  :key="index"
                  class="grid gap-2 md:grid-cols-[1fr_1fr_auto]"
              >
                <Input v-model="row.value" placeholder="value"/>
                <Input v-model="row.label" placeholder="Label"/>
                <Button type="button" variant="ghost" size="icon" @click="removeOptionRow(index)">
                  <Trash2 class="size-4"/>
                </Button>
              </div>
            </section>
          </div>

          <SheetFooter class="sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" @click="closeCreateFieldDialog">
              Cancel
            </Button>
            <Button type="submit" :disabled="isCreatingField">
              <Loader2 v-if="isCreatingField" class="size-4 animate-spin"/>
              Create
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  </SettingsLayout>
</template>
