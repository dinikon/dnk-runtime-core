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
  X
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
      ? "bg-orange-50 text-orange-700 ring-orange-100"
      : "bg-blue-50 text-blue-700 ring-blue-100";
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
      <div v-if="isLoading" class="grid flex-1 place-items-center text-sm text-neutral-400">
        <span class="inline-flex items-center gap-2">
          <Loader2 class="size-4 animate-spin"/>
          Loading object...
        </span>
      </div>

      <div v-else-if="object" class="flex flex-1 flex-col">
        <header class="flex items-start justify-between gap-4">
          <div class="flex min-w-0 items-center gap-3">
            <span class="grid size-7 shrink-0 place-items-center rounded-md bg-purple-50 text-purple-600">
              <Database class="size-4"/>
            </span>
            <div class="min-w-0">
              <div class="flex min-w-0 items-center gap-2">
                <h1 class="truncate text-base font-semibold text-neutral-900">{{ object.plural_label }}</h1>
                <span
                    class="inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1"
                    :class="kindClass(object.kind)"
                >
                  {{ kindLabel(object.kind) }}
                </span>
              </div>
              <p class="mt-1 truncate text-sm text-neutral-400">{{ object.description || object.plural_name }}</p>
            </div>
          </div>

          <div class="flex shrink-0 items-center gap-2">
            <RouterLink
                class="inline-flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-600 transition-colors hover:bg-neutral-50"
                :to="{path: '/', query: {object: object.id}}"
            >
              <ExternalLink class="size-4"/>
              See records
            </RouterLink>
            <button
                v-if="canDeleteCurrentObject"
                class="inline-flex h-8 items-center gap-1.5 rounded-md border border-red-200 bg-white px-3 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                :disabled="isDeletingObject"
                @click="deleteCurrentObject"
            >
              <Loader2 v-if="isDeletingObject" class="size-4 animate-spin"/>
              <Trash2 v-else class="size-4"/>
              Delete
            </button>
            <button
                class="inline-flex h-8 items-center gap-1.5 rounded-md bg-blue-600 px-3 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-neutral-300"
                type="button"
                :disabled="!canManageFields"
                @click="openCreateFieldDialog"
            >
              <Plus class="size-4"/>
              New Field
            </button>
          </div>
        </header>

        <div v-if="pageError" class="mt-5 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {{ pageError }}
        </div>

        <nav class="mt-8 flex items-center gap-5 border-b border-neutral-200 text-sm font-semibold">
          <button class="-mb-px inline-flex h-9 items-center gap-1.5 border-b border-neutral-900 text-neutral-900"
                  type="button">
            <Database class="size-4"/>
            Fields
          </button>
          <button class="inline-flex h-9 items-center gap-1.5 text-neutral-500" type="button" disabled>
            <Shield class="size-4"/>
            Permissions
          </button>
          <button class="inline-flex h-9 items-center gap-1.5 text-neutral-500" type="button" disabled>
            <Settings class="size-4"/>
            Settings
          </button>
        </nav>

        <section class="mt-7 grid gap-5">
          <div class="grid gap-1">
            <h2 class="text-sm font-semibold text-neutral-900">Fields</h2>
            <p class="text-sm text-neutral-400">Customize fields available in object views and records</p>
          </div>

          <label class="relative max-w-3xl">
            <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-300"/>
            <input
                v-model="searchQuery"
                class="h-9 w-full rounded-md border border-neutral-200 bg-white pl-9 pr-3 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-300 focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="Search a field..."
            />
          </label>

          <div class="max-w-5xl overflow-hidden rounded-md border border-neutral-100">
            <table class="w-full border-collapse text-left text-sm">
              <thead class="bg-white text-xs font-semibold text-neutral-400">
              <tr class="border-b border-neutral-100">
                <th class="px-3 py-2">Name</th>
                <th class="px-3 py-2">Identifier</th>
                <th class="px-3 py-2">Data type</th>
                <th class="w-28 px-3 py-2">Required</th>
                <th class="w-16 px-3 py-2"/>
              </tr>
              </thead>
              <tbody>
              <tr v-if="filteredFields.length === 0">
                <td class="px-3 py-10 text-center text-neutral-400" colspan="5">No fields found.</td>
              </tr>
              <tr
                  v-for="field in filteredFields"
                  v-else
                  :key="field.id"
                  class="h-11 border-b border-neutral-100 text-neutral-700 last:border-b-0"
              >
                <td class="px-3 py-2">
                  <div class="flex min-w-0 items-center gap-2">
                    <span class="truncate font-medium">{{ field.label }}</span>
                    <span
                        class="inline-flex shrink-0 items-center rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-semibold text-neutral-500"
                    >
                        {{ fieldKindLabel(field.kind) }}
                      </span>
                  </div>
                </td>
                <td class="px-3 py-2">
                  <code class="text-xs text-neutral-500">{{ field.field_name }}</code>
                </td>
                <td class="px-3 py-2">
                    <span class="rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-700">
                      {{ fieldTypeLabel(field.type) }}
                    </span>
                </td>
                <td class="px-3 py-2 text-neutral-500">{{ field.is_nullable ? "Optional" : "Required" }}</td>
                <td class="px-3 py-2">
                  <button
                      v-if="canDeleteField(field)"
                      class="grid size-7 place-items-center rounded-md text-neutral-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      :disabled="deletingFieldId === field.id"
                      @click="deleteField(field)"
                  >
                    <Loader2 v-if="deletingFieldId === field.id" class="size-4 animate-spin"/>
                    <Trash2 v-else class="size-4"/>
                  </button>
                </td>
              </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div v-else class="grid flex-1 place-items-center text-sm text-neutral-400">
        Object is not available.
      </div>
    </div>

    <div
        v-if="isCreateFieldDialogOpen"
        class="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-neutral-950/30 px-4 py-8"
        role="dialog"
        aria-modal="true"
    >
      <form
          class="w-full max-w-2xl rounded-lg border border-neutral-200 bg-white p-5 shadow-xl"
          @submit.prevent="submitCreateField"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="grid gap-1">
            <h2 class="text-base font-semibold text-neutral-900">New Field</h2>
            <p class="text-sm text-neutral-400">{{ object?.plural_label }}</p>
          </div>
          <button
              class="grid size-8 place-items-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
              type="button"
              @click="closeCreateFieldDialog"
          >
            <X class="size-4"/>
          </button>
        </div>

        <div v-if="createFieldErrors.length > 0" class="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          <p v-for="error in createFieldErrors" :key="error">{{ error }}</p>
        </div>

        <div class="mt-5 grid gap-4 md:grid-cols-2">
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Label</span>
            <input
                v-model="fieldForm.label"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="Status"
            />
          </label>
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Identifier</span>
            <input
                v-model="fieldForm.field_name"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="status"
            />
          </label>
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Data type</span>
            <select
                v-model="fieldForm.type"
                class="h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
            >
              <option v-for="type in FIELD_TYPES" :key="type" :value="type">
                {{ fieldTypeLabel(type) }}
              </option>
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Default value</span>
            <input
                v-model="fieldForm.default_value"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="Optional"
            />
          </label>
        </div>

        <label class="mt-4 flex items-center gap-2 text-sm font-medium text-neutral-700">
          <input
              v-model="fieldForm.is_required"
              class="size-4 rounded border-neutral-300"
              type="checkbox"
          />
          Required
        </label>

        <label class="mt-4 grid gap-1">
          <span class="text-xs font-semibold text-neutral-400">Description</span>
          <textarea
              v-model="fieldForm.description"
              class="min-h-20 rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
              placeholder="Optional"
          />
        </label>

        <section v-if="isSelectLikeField" class="mt-5 grid gap-3 rounded-md border border-neutral-100 p-3">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-neutral-900">Options</h3>
            <button
                class="inline-flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-600 transition-colors hover:bg-neutral-50"
                type="button"
                @click="addOptionRow"
            >
              <Plus class="size-4"/>
              Add option
            </button>
          </div>
          <div
              v-for="(row, index) in optionRows"
              :key="index"
              class="grid gap-2 md:grid-cols-[1fr_1fr_auto]"
          >
            <input
                v-model="row.value"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="value"
            />
            <input
                v-model="row.label"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="Label"
            />
            <button
                class="grid size-9 place-items-center rounded-md text-neutral-400 transition-colors hover:bg-red-50 hover:text-red-600"
                type="button"
                @click="removeOptionRow(index)"
            >
              <Trash2 class="size-4"/>
            </button>
          </div>
        </section>

        <div class="mt-5 flex justify-end gap-2">
          <button
              class="inline-flex h-8 items-center rounded-md border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-600 transition-colors hover:bg-neutral-50"
              type="button"
              @click="closeCreateFieldDialog"
          >
            Cancel
          </button>
          <button
              class="inline-flex h-8 items-center gap-1.5 rounded-md bg-neutral-900 px-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
              type="submit"
              :disabled="isCreatingField"
          >
            <Loader2 v-if="isCreatingField" class="size-4 animate-spin"/>
            Create
          </button>
        </div>
      </form>
    </div>
  </SettingsLayout>
</template>
