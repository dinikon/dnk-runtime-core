<script setup lang="ts">
import {computed, onMounted, reactive, ref} from "vue";
import {useRoute, useRouter} from "vue-router";
import {ChevronRight, Database, Filter, Loader2, Plus, Search, Trash2} from "lucide-vue-next";

import {useSessionStore} from "@/app/stores/session";
import {getApiErrorMessage, getApiErrorStatus} from "@/api/http/errors";
import {schemaRegistryApi, type CreateCustomObjectPayload, type RuntimeObject} from "@/api/schema-registry";
import {Alert, AlertDescription} from "@/components/ui/alert";
import {Button} from "@/components/ui/button";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
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

function handleCreateSheetOpen(open: boolean) {
  if (open) {
    openCreateDialog();
    return;
  }

  closeCreateDialog();
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
      ? "bg-secondary text-secondary-foreground ring-border"
      : "bg-muted text-muted-foreground ring-border";
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
          <h1 class="text-base font-semibold">Objects</h1>
          <div class="grid gap-1">
            <h2 class="text-sm font-semibold">Existing objects</h2>
            <p class="text-sm text-muted-foreground">Manage objects, fields and relationships</p>
          </div>
        </div>

        <Button type="button" size="sm" @click="openCreateDialog">
          <Plus class="size-4"/>
          New Object
        </Button>
      </header>

      <Alert v-if="routeNotice" class="mt-5">
        <AlertDescription>{{ routeNotice }}</AlertDescription>
      </Alert>
      <Alert v-if="pageError" class="mt-5" variant="destructive">
        <AlertDescription>{{ pageError }}</AlertDescription>
      </Alert>

      <div class="mt-6 flex items-center gap-2">
        <div class="relative min-w-0 flex-1">
          <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"/>
          <Input v-model="searchQuery" class="pl-9" placeholder="Search an object..."/>
        </div>
        <Button type="button" variant="outline" size="icon" disabled>
          <Filter class="size-4"/>
        </Button>
      </div>

      <div class="mt-3 overflow-hidden rounded-md border">
        <table class="w-full border-collapse text-left text-sm">
          <thead class="bg-background text-xs font-semibold text-muted-foreground">
          <tr class="border-b">
            <th class="px-3 py-2">Name</th>
            <th class="px-3 py-2">App</th>
            <th class="w-24 px-3 py-2 text-right">Fields</th>
            <th class="w-20 px-3 py-2"/>
          </tr>
          </thead>
          <tbody>
          <tr v-if="isLoading">
            <td class="px-3 py-10 text-center text-muted-foreground" colspan="4">
              <span class="inline-flex items-center gap-2">
                <Loader2 class="size-4 animate-spin"/>
                Loading objects...
              </span>
            </td>
          </tr>

          <tr v-else-if="filteredObjects.length === 0">
            <td class="px-3 py-10 text-center text-muted-foreground" colspan="4">No objects found.</td>
          </tr>

          <tr
              v-for="object in filteredObjects"
              v-else
              :key="object.id"
              class="h-11 cursor-pointer border-b text-foreground transition-colors last:border-b-0 hover:bg-muted/50"
              tabindex="0"
              @click="openObject(object)"
              @keydown.enter="openObject(object)"
          >
            <td class="px-3 py-2">
              <div class="flex min-w-0 items-center gap-2">
                <span class="grid size-5 shrink-0 place-items-center rounded bg-muted text-muted-foreground">
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
            <td class="px-3 py-2 text-right text-muted-foreground">{{ object.fields.length }}</td>
            <td class="px-3 py-2">
              <div class="flex items-center justify-end gap-1">
                <Button
                    v-if="canDeleteObject(object)"
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    :disabled="deletingObjectId === object.id"
                    @click.stop="deleteObject(object)"
                >
                  <Loader2 v-if="deletingObjectId === object.id" class="size-4 animate-spin"/>
                  <Trash2 v-else class="size-4"/>
                </Button>
                <ChevronRight class="size-4 text-muted-foreground"/>
              </div>
            </td>
          </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Sheet :open="isCreateDialogOpen" @update:open="handleCreateSheetOpen">
      <SheetContent class="w-full overflow-y-auto sm:max-w-xl">
        <form class="flex min-h-full flex-col" @submit.prevent="submitCreateObject">
          <SheetHeader>
            <SheetTitle>New Object</SheetTitle>
            <SheetDescription>Create a custom runtime object</SheetDescription>
          </SheetHeader>

          <div class="grid gap-5 px-4">
            <Alert v-if="createErrors.length > 0" variant="destructive">
              <AlertDescription class="grid gap-1">
                <span v-for="error in createErrors" :key="error">{{ error }}</span>
              </AlertDescription>
            </Alert>

            <div class="grid gap-4 md:grid-cols-2">
              <div class="grid gap-2">
                <Label for="object-singular-label">Singular label</Label>
                <Input id="object-singular-label" v-model="createForm.singular_label" placeholder="Company"/>
              </div>
              <div class="grid gap-2">
                <Label for="object-plural-label">Plural label</Label>
                <Input id="object-plural-label" v-model="createForm.plural_label" placeholder="Companies"/>
              </div>
              <div class="grid gap-2">
                <Label for="object-singular-name">Singular identifier</Label>
                <Input id="object-singular-name" v-model="createForm.singular_name" placeholder="company"/>
              </div>
              <div class="grid gap-2">
                <Label for="object-plural-name">Plural identifier</Label>
                <Input id="object-plural-name" v-model="createForm.plural_name" placeholder="companies"/>
              </div>
            </div>

            <div class="grid gap-2">
              <Label for="object-description">Description</Label>
              <Textarea id="object-description" v-model="createForm.description" placeholder="Optional"/>
            </div>
          </div>

          <SheetFooter class="sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" @click="closeCreateDialog">
              Cancel
            </Button>
            <Button type="submit" :disabled="isCreating">
              <Loader2 v-if="isCreating" class="size-4 animate-spin"/>
              Create
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  </SettingsLayout>
</template>
