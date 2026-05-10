<script setup lang="ts">
import {computed, onMounted, ref, watch} from "vue";
import {useRoute, useRouter} from "vue-router";
import {RefreshCcw} from "lucide-vue-next";

import {ConsoleSidebar, ObjectRecordsTable, ObjectTabs} from "@/components/app";
import {useSessionStore} from "@/app/stores/session";
import {getApiErrorMessage, getApiErrorStatus} from "@/shared/api/http/errors";
import {
  isObjectRecordsAdapterNotFoundError,
  objectRecordsApi,
  type ObjectRecord
} from "@/shared/api/object-records";
import {schemaRegistryApi, type RuntimeField, type RuntimeObject} from "@/shared/api/schema-registry";

const DEFAULT_LIMIT = 50;
const DEFAULT_OFFSET = 0;

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();

const objects = ref<RuntimeObject[]>([]);
const selectedObjectId = ref<string | null>(null);
const selectedSchema = ref<RuntimeObject | null>(null);
const records = ref<ObjectRecord[]>([]);
const recordsCount = ref(0);
const isLoadingObjects = ref(false);
const isLoadingSchema = ref(false);
const isLoadingRecords = ref(false);
const pageError = ref<string | null>(null);
const recordsError = ref<string | null>(null);

let objectLoadRequest = 0;

const visibleObjects = computed(() => objects.value.filter((object) => isVisibleObjectKind(object.kind)));
const selectedObject = computed(() => (
    visibleObjects.value.find((object) => object.id === selectedObjectId.value) ?? null
));
const tableFields = computed<RuntimeField[]>(() => (
    selectedSchema.value?.fields.filter((field) => field.kind.trim().toLowerCase() !== "system") ?? []
));
const hasRecoverableError = computed(() => pageError.value !== null);

onMounted(() => {
  void loadObjects();
});

watch(
    () => route.query.object,
    () => {
      if (!isLoadingObjects.value && objects.value.length > 0) {
        selectObjectFromRoute();
      }
    }
);

async function loadObjects() {
  isLoadingObjects.value = true;
  pageError.value = null;
  recordsError.value = null;

  try {
    const result = await schemaRegistryApi.listObjects();
    objects.value = result.items;
    selectObjectFromRoute();
  } catch (error) {
    await handleApiFailure(error, "Could not load objects.");
  } finally {
    isLoadingObjects.value = false;
  }
}

function selectObject(object: RuntimeObject) {
  void router.push({
    query: {
      ...route.query,
      object: object.id
    }
  });
}

function selectObjectFromRoute() {
  const fallbackObject = visibleObjects.value[0] ?? null;
  if (!fallbackObject) {
    selectedObjectId.value = null;
    selectedSchema.value = null;
    records.value = [];
    recordsCount.value = 0;
    return;
  }

  const queryObjectId = readObjectIdFromRoute();
  const nextObject = visibleObjects.value.find((object) => object.id === queryObjectId) ?? fallbackObject;

  if (queryObjectId !== nextObject.id) {
    void router.replace({
      query: {
        ...route.query,
        object: nextObject.id
      }
    });
  }

  if (selectedObjectId.value === nextObject.id) {
    return;
  }

  selectedObjectId.value = nextObject.id;
  void loadObjectWorkspace(nextObject);
}

async function loadObjectWorkspace(object: RuntimeObject) {
  const requestId = ++objectLoadRequest;
  selectedSchema.value = null;
  records.value = [];
  recordsCount.value = 0;
  pageError.value = null;
  recordsError.value = null;
  isLoadingSchema.value = true;

  try {
    const schema = await schemaRegistryApi.describeObject(object.id);
    if (requestId !== objectLoadRequest) {
      return;
    }

    selectedSchema.value = schema;
    isLoadingSchema.value = false;
    await loadRecords(schema, requestId);
  } catch (error) {
    if (requestId === objectLoadRequest) {
      await handleApiFailure(error, "Could not load object schema.");
    }
  } finally {
    if (requestId === objectLoadRequest) {
      isLoadingSchema.value = false;
    }
  }
}

async function loadRecords(object: RuntimeObject, requestId = objectLoadRequest) {
  isLoadingRecords.value = true;
  recordsError.value = null;

  try {
    const result = await objectRecordsApi.list(object, {
      limit: DEFAULT_LIMIT,
      offset: DEFAULT_OFFSET
    });

    if (requestId !== objectLoadRequest) {
      return;
    }

    records.value = result.items;
    recordsCount.value = result.count;
  } catch (error) {
    if (requestId !== objectLoadRequest) {
      return;
    }

    if (isObjectRecordsAdapterNotFoundError(error)) {
      recordsError.value = "Data endpoint is not configured.";
      return;
    }

    await handleApiFailure(error, "Could not load records.");
  } finally {
    if (requestId === objectLoadRequest) {
      isLoadingRecords.value = false;
    }
  }
}

async function retryCurrentLoad() {
  if (selectedObject.value) {
    await loadObjectWorkspace(selectedObject.value);
    return;
  }

  await loadObjects();
}

function readObjectIdFromRoute(): string | null {
  return typeof route.query.object === "string" ? route.query.object : null;
}

function isVisibleObjectKind(kind: string): boolean {
  const normalizedKind = kind.trim().toLowerCase();
  return normalizedKind === "standard" || normalizedKind === "custom";
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
  <div class="flex h-screen overflow-hidden bg-neutral-100 text-neutral-900">
    <ConsoleSidebar/>

    <main class="flex min-w-0 flex-1 flex-col gap-3 p-4">
      <header class="flex min-h-10 items-center gap-3 px-1">
        <div class="min-w-0">
          <h1 class="truncate text-base font-semibold text-neutral-800">Objects</h1>
        </div>

        <button
            v-if="hasRecoverableError"
            type="button"
            class="ml-auto inline-flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-sm font-medium text-neutral-700 shadow-sm transition-colors hover:bg-neutral-50"
            @click="retryCurrentLoad"
        >
          <RefreshCcw class="size-4"/>
          Retry
        </button>
      </header>

      <ObjectTabs
          :objects="visibleObjects"
          :selected-object-id="selectedObjectId"
          :is-loading="isLoadingObjects"
          @select="selectObject"
      />

      <p v-if="pageError" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ pageError }}
      </p>

      <ObjectRecordsTable
          :object="selectedSchema ?? selectedObject"
          :fields="tableFields"
          :records="records"
          :count="recordsCount"
          :is-loading-schema="isLoadingSchema"
          :is-loading-records="isLoadingRecords"
          :records-error="recordsError"
      />
    </main>
  </div>
</template>
