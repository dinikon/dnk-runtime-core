<script setup lang="ts">
import {computed, onMounted, reactive, ref} from "vue";
import {useRoute, useRouter} from "vue-router";
import {ChevronRight, Database, Filter, Loader2, Plus, Search, Trash2, X} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {schemaRegistryApi, type CreateCustomObjectPayload, type RuntimeObject} from "@/api/schema-registry";
import {SettingsLayout} from "@/layouts";

const IDENTIFIER_PATTERN = /^[a-z][a-z0-9_]*$/;

const router = useRouter();
const route = useRoute();
const sessionStore = useSessionStore();

const objects = ref<RuntimeObject[]>([]);
const isLoading = ref(false);
const isCreating = ref(false);
const deletingObjectId = ref<string | null>(null);
const pageError = ref<string | null>(null);
const createErrors = ref<string[]>([]);
const searchQuery = ref("");
const isCreateDialogOpen = ref(false);
const createForm = reactive({
  singular_label: "",
  plural_label: "",
  singular_name: "",
  plural_name: "",
  description: ""
});

const routeNotice = computed(() => (
    route.query.error === "object-not-found" ? "Object was not found." : null
));
const visibleObjects = computed(() => objects.value.filter((object) => isManagedObjectKind(object.kind)));
const filteredObjects = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();

  if (!query) {
    return visibleObjects.value;
  }

  return visibleObjects.value.filter((object) => (
      object.plural_label.toLowerCase().includes(query) ||
      object.singular_label.toLowerCase().includes(query) ||
      object.plural_name.toLowerCase().includes(query) ||
      object.singular_name.toLowerCase().includes(query)
  ));
});

onMounted(() => {
  void loadObjects();
});

async function loadObjects() {
  isLoading.value = true;
  pageError.value = null;

  try {
    const result = await schemaRegistryApi.listObjects();
    objects.value = result.items;
  } catch (error) {
    await handleApiFailure(error, "Could not load objects.");
  } finally {
    isLoading.value = false;
  }
}

function openCreateDialog() {
  resetCreateForm();
  isCreateDialogOpen.value = true;
}

function closeCreateDialog() {
  if (isCreating.value) {
    return;
  }

  isCreateDialogOpen.value = false;
}

async function submitCreateObject() {
  const errors = validateCreateObjectForm();
  createErrors.value = errors;

  if (errors.length > 0) {
    return;
  }

  isCreating.value = true;

  const payload: CreateCustomObjectPayload = {
    singular_label: createForm.singular_label.trim(),
    plural_label: createForm.plural_label.trim(),
    singular_name: createForm.singular_name.trim(),
    plural_name: createForm.plural_name.trim(),
    description: createForm.description.trim(),
    fields: []
  };

  try {
    const createdObject = await schemaRegistryApi.createObject(payload);
    objects.value = [...objects.value, createdObject];
    isCreateDialogOpen.value = false;
    await router.push(`/settings/workspace/data-model/${createdObject.id}`);
  } catch (error) {
    if (getApiErrorStatus(error) === 401) {
      sessionStore.clearSession();
      await router.push("/login");
      return;
    }

    createErrors.value = [getApiErrorMessage(error, "Could not create object.")];
  } finally {
    isCreating.value = false;
  }
}

async function deleteObject(object: RuntimeObject) {
  if (!canDeleteObject(object) || deletingObjectId.value) {
    return;
  }

  const confirmed = window.confirm(`Delete ${object.plural_label}? This will permanently remove the object table.`);
  if (!confirmed) {
    return;
  }

  deletingObjectId.value = object.id;
  pageError.value = null;

  try {
    await schemaRegistryApi.deleteObject(object.id);
    objects.value = objects.value.filter((item) => item.id !== object.id);
  } catch (error) {
    await handleApiFailure(error, "Could not delete object.");
  } finally {
    deletingObjectId.value = null;
  }
}

function openObject(object: RuntimeObject) {
  void router.push(`/settings/workspace/data-model/${object.id}`);
}

function resetCreateForm() {
  createForm.singular_label = "";
  createForm.plural_label = "";
  createForm.singular_name = "";
  createForm.plural_name = "";
  createForm.description = "";
  createErrors.value = [];
}

function validateCreateObjectForm(): string[] {
  const errors: string[] = [];
  const singularLabel = createForm.singular_label.trim();
  const pluralLabel = createForm.plural_label.trim();
  const singularName = createForm.singular_name.trim();
  const pluralName = createForm.plural_name.trim();

  validateLabel(singularLabel, "Singular label", errors);
  validateLabel(pluralLabel, "Plural label", errors);

  if (singularLabel && pluralLabel && singularLabel === pluralLabel) {
    errors.push("Singular label and plural label must be different.");
  }

  validateIdentifier(singularName, "Singular identifier", errors);
  validateIdentifier(pluralName, "Plural identifier", errors);

  if (singularName && pluralName && singularName === pluralName) {
    errors.push("Singular identifier and plural identifier must be different.");
  }

  if (pluralName && !pluralName.endsWith("s")) {
    errors.push("Plural identifier must end with s.");
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

function isManagedObjectKind(kind: string): boolean {
  const normalizedKind = kind.trim().toLowerCase();
  return normalizedKind === "standard" || normalizedKind === "custom";
}

function canDeleteObject(object: RuntimeObject): boolean {
  return object.kind.trim().toLowerCase() === "custom";
}

function kindLabel(kind: string): string {
  return kind.trim().toLowerCase() === "custom" ? "Custom" : "Standard";
}

function kindClass(kind: string): string {
  return kind.trim().toLowerCase() === "custom"
      ? "bg-orange-50 text-orange-700 ring-orange-100"
      : "bg-blue-50 text-blue-700 ring-blue-100";
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
      title="Data Model"
      active-item="data-model"
      :breadcrumbs="[{label: 'Workspace'}, {label: 'Data Model'}]"
  >
    <div class="flex min-h-[560px] flex-col">
      <header class="flex items-start justify-between gap-4">
        <div class="grid gap-7">
          <h1 class="text-base font-semibold text-neutral-900">Objects</h1>
          <div class="grid gap-1">
            <h2 class="text-sm font-semibold text-neutral-900">Existing objects</h2>
            <p class="text-sm text-neutral-400">Manage objects, fields and relationships</p>
          </div>
        </div>

        <button
            class="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md bg-blue-600 px-3 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
            type="button"
            @click="openCreateDialog"
        >
          <Plus class="size-4"/>
          New Object
        </button>
      </header>

      <div v-if="routeNotice" class="mt-5 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
        {{ routeNotice }}
      </div>
      <div v-if="pageError" class="mt-5 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ pageError }}
      </div>

      <div class="mt-6 flex items-center gap-2">
        <label class="relative min-w-0 flex-1">
          <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-300"/>
          <input
              v-model="searchQuery"
              class="h-9 w-full rounded-md border border-neutral-200 bg-white pl-9 pr-3 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-300 focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
              placeholder="Search an object..."
          />
        </label>
        <button
            class="grid size-9 place-items-center rounded-md border border-neutral-200 bg-white text-neutral-500 transition-colors hover:bg-neutral-50"
            type="button"
            disabled
        >
          <Filter class="size-4"/>
        </button>
      </div>

      <div class="mt-3 overflow-hidden rounded-md border border-neutral-100">
        <table class="w-full border-collapse text-left text-sm">
          <thead class="bg-white text-xs font-semibold text-neutral-400">
          <tr class="border-b border-neutral-100">
            <th class="px-3 py-2">Name</th>
            <th class="px-3 py-2">App</th>
            <th class="w-24 px-3 py-2 text-right">Fields</th>
            <th class="w-20 px-3 py-2"/>
          </tr>
          </thead>
          <tbody>
          <tr v-if="isLoading">
            <td class="px-3 py-10 text-center text-neutral-400" colspan="4">
                <span class="inline-flex items-center gap-2">
                  <Loader2 class="size-4 animate-spin"/>
                  Loading objects...
                </span>
            </td>
          </tr>

          <tr v-else-if="filteredObjects.length === 0">
            <td class="px-3 py-10 text-center text-neutral-400" colspan="4">No objects found.</td>
          </tr>

          <tr
              v-for="object in filteredObjects"
              v-else
              :key="object.id"
              class="h-11 cursor-pointer border-b border-neutral-100 text-neutral-700 transition-colors last:border-b-0 hover:bg-neutral-50"
              tabindex="0"
              @click="openObject(object)"
              @keydown.enter="openObject(object)"
          >
            <td class="px-3 py-2">
              <div class="flex min-w-0 items-center gap-2">
                  <span class="grid size-5 shrink-0 place-items-center rounded bg-blue-50 text-blue-600">
                    <Database class="size-3.5"/>
                  </span>
                <span class="truncate font-medium">{{ object.plural_label }}</span>
              </div>
            </td>
            <td class="px-3 py-2">
                <span
                    class="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1"
                    :class="kindClass(object.kind)"
                >
                  {{ kindLabel(object.kind) }}
                </span>
            </td>
            <td class="px-3 py-2 text-right text-neutral-500">{{ object.fields.length }}</td>
            <td class="px-3 py-2">
              <div class="flex items-center justify-end gap-1">
                <button
                    v-if="canDeleteObject(object)"
                    class="grid size-7 place-items-center rounded-md text-neutral-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                    type="button"
                    :disabled="deletingObjectId === object.id"
                    @click.stop="deleteObject(object)"
                >
                  <Loader2 v-if="deletingObjectId === object.id" class="size-4 animate-spin"/>
                  <Trash2 v-else class="size-4"/>
                </button>
                <ChevronRight class="size-4 text-neutral-300"/>
              </div>
            </td>
          </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
        v-if="isCreateDialogOpen"
        class="fixed inset-0 z-50 grid place-items-center bg-neutral-950/30 px-4"
        role="dialog"
        aria-modal="true"
    >
      <form
          class="w-full max-w-xl rounded-lg border border-neutral-200 bg-white p-5 shadow-xl"
          @submit.prevent="submitCreateObject"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="grid gap-1">
            <h2 class="text-base font-semibold text-neutral-900">New Object</h2>
            <p class="text-sm text-neutral-400">Create a custom runtime object</p>
          </div>
          <button
              class="grid size-8 place-items-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
              type="button"
              @click="closeCreateDialog"
          >
            <X class="size-4"/>
          </button>
        </div>

        <div v-if="createErrors.length > 0" class="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          <p v-for="error in createErrors" :key="error">{{ error }}</p>
        </div>

        <div class="mt-5 grid gap-4 md:grid-cols-2">
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Singular label</span>
            <input
                v-model="createForm.singular_label"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="Company"
            />
          </label>
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Plural label</span>
            <input
                v-model="createForm.plural_label"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="Companies"
            />
          </label>
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Singular identifier</span>
            <input
                v-model="createForm.singular_name"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="company"
            />
          </label>
          <label class="grid gap-1">
            <span class="text-xs font-semibold text-neutral-400">Plural identifier</span>
            <input
                v-model="createForm.plural_name"
                class="h-9 rounded-md border border-neutral-200 px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
                placeholder="companies"
            />
          </label>
        </div>

        <label class="mt-4 grid gap-1">
          <span class="text-xs font-semibold text-neutral-400">Description</span>
          <textarea
              v-model="createForm.description"
              class="min-h-20 rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
              placeholder="Optional"
          />
        </label>

        <div class="mt-5 flex justify-end gap-2">
          <button
              class="inline-flex h-8 items-center rounded-md border border-neutral-200 bg-white px-3 text-sm font-semibold text-neutral-600 transition-colors hover:bg-neutral-50"
              type="button"
              @click="closeCreateDialog"
          >
            Cancel
          </button>
          <button
              class="inline-flex h-8 items-center gap-1.5 rounded-md bg-neutral-900 px-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
              type="submit"
              :disabled="isCreating"
          >
            <Loader2 v-if="isCreating" class="size-4 animate-spin"/>
            Create
          </button>
        </div>
      </form>
    </div>
  </SettingsLayout>
</template>
