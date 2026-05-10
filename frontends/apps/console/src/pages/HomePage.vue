<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref} from "vue";
import {useRouter} from "vue-router";

import {
  ConsoleSidebar,
  ContactDetailsPanel,
  ContactsTable,
  type ContactFormValue,
  type ContactTableLabels,
  type ContactTableRow
} from "@/components/app";
import {useSessionStore} from "@/app/stores/session";
import {
  crmContactsApi,
  type Contact,
  type ContactFieldOption,
  type ContactFieldsResponse
} from "@/shared/api/crm";
import {getApiErrorMessage, getApiErrorStatus} from "@/shared/api/http/errors";

const DETAILS_WIDTH_STORAGE_KEY = "console.contacts.details.width";
const DRAFT_ROW_KEY = "draft-contact";
const DETAILS_MIN_WIDTH = 360;
const DETAILS_MAX_WIDTH = 720;

const router = useRouter();
const sessionStore = useSessionStore();

const contacts = ref<Contact[]>([]);
const contactsCount = ref(0);
const fields = ref<ContactFieldsResponse | null>(null);
const selectedKey = ref<string | null>(null);
const draftRow = ref<ContactTableRow | null>(null);
const isLoading = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const pageError = ref<string | null>(null);
const detailsError = ref<string | null>(null);
const detailsWidth = ref(readStoredDetailsWidth());
const isResizing = ref(false);

const rows = computed<ContactTableRow[]>(() => {
  const contactRows = contacts.value.map(contactToRow);
  return draftRow.value ? [draftRow.value, ...contactRows] : contactRows;
});

const selectedRow = computed(() => rows.value.find((row) => row.key === selectedKey.value) ?? null);
const tableCount = computed(() => contactsCount.value + (draftRow.value ? 1 : 0));
const statusOptions = computed(() => fieldOptions("status", [
  {value: "lead", label: "Lead"},
  {value: "customer", label: "Customer"},
  {value: "partner", label: "Partner"}
]));
const tagOptions = computed(() => fieldOptions("tags", [
  {value: "vip", label: "VIP"},
  {value: "newsletter", label: "Newsletter"},
  {value: "inactive", label: "Inactive"}
]));
const tableLabels = computed<ContactTableLabels>(() => ({
  name: contactNameLabel(),
  status: fieldLabel("status", "Status"),
  tags: fieldLabel("tags", "Tags"),
  createdAt: fieldLabel("created_at", "Created At"),
  updatedAt: fieldLabel("updated_at", "Updated At")
}));

onMounted(() => {
  void loadWorkspace();
});

onBeforeUnmount(() => {
  stopResize();
});

async function loadWorkspace() {
  isLoading.value = true;
  pageError.value = null;

  try {
    const [fieldsResult, contactsResult] = await Promise.all([
      crmContactsApi.describeFields(),
      crmContactsApi.list({limit: 50, offset: 0})
    ]);
    fields.value = fieldsResult;
    contacts.value = contactsResult.items;
    contactsCount.value = contactsResult.count;
  } catch (error) {
    await handleApiFailure(error, "Could not load contacts.");
  } finally {
    isLoading.value = false;
  }
}

function createDraftRow() {
  detailsError.value = null;

  if (!draftRow.value) {
    draftRow.value = {
      key: DRAFT_ROW_KEY,
      contact: null,
      isDraft: true,
      firstName: "",
      lastName: null,
      middleName: null,
      status: null,
      tags: [],
      createdAt: null,
      updatedAt: null
    };
  }

  selectedKey.value = DRAFT_ROW_KEY;
}

function selectRow(row: ContactTableRow) {
  detailsError.value = null;
  selectedKey.value = row.key;
}

function closeDetails() {
  if (selectedKey.value === DRAFT_ROW_KEY) {
    draftRow.value = null;
  }

  selectedKey.value = null;
  detailsError.value = null;
}

async function saveContact(value: ContactFormValue) {
  if (!selectedRow.value) {
    return;
  }

  isSaving.value = true;
  detailsError.value = null;

  try {
    if (selectedRow.value.isDraft) {
      const created = await crmContactsApi.create({
        first_name: value.first_name,
        last_name: value.last_name,
        middle_name: value.middle_name,
        status: value.status,
        tags: value.tags
      });
      contacts.value = [created, ...contacts.value];
      contactsCount.value += 1;
      draftRow.value = null;
      selectedKey.value = created.id;
      return;
    }

    const updated = await crmContactsApi.update(selectedRow.value.key, {
      first_name: value.first_name,
      last_name: value.last_name,
      middle_name: value.middle_name,
      status: value.status,
      tags: value.tags
    });
    contacts.value = contacts.value.map((contact) => contact.id === updated.id ? updated : contact);
    selectedKey.value = updated.id;
  } catch (error) {
    await handleApiFailure(error, "Could not save contact.", "details");
  } finally {
    isSaving.value = false;
  }
}

async function deleteSelectedContact() {
  const row = selectedRow.value;

  if (!row || row.isDraft) {
    closeDetails();
    return;
  }

  isDeleting.value = true;
  detailsError.value = null;

  try {
    await crmContactsApi.delete(row.key);
    contacts.value = contacts.value.filter((contact) => contact.id !== row.key);
    contactsCount.value = Math.max(contactsCount.value - 1, 0);
    selectedKey.value = null;
  } catch (error) {
    await handleApiFailure(error, "Could not delete contact.", "details");
  } finally {
    isDeleting.value = false;
  }
}

function startResize(event: MouseEvent) {
  event.preventDefault();
  isResizing.value = true;
  window.addEventListener("mousemove", resizeDetails);
  window.addEventListener("mouseup", stopResize);
}

function resizeDetails(event: MouseEvent) {
  if (!isResizing.value) {
    return;
  }

  const nextWidth = clamp(window.innerWidth - event.clientX - 24, DETAILS_MIN_WIDTH, DETAILS_MAX_WIDTH);
  detailsWidth.value = nextWidth;
  window.localStorage.setItem(DETAILS_WIDTH_STORAGE_KEY, String(nextWidth));
}

function stopResize() {
  isResizing.value = false;
  window.removeEventListener("mousemove", resizeDetails);
  window.removeEventListener("mouseup", stopResize);
}

function contactToRow(contact: Contact): ContactTableRow {
  return {
    key: contact.id,
    contact,
    isDraft: false,
    firstName: contact.first_name,
    lastName: contact.last_name,
    middleName: contact.middle_name,
    status: contact.status,
    tags: contact.tags,
    createdAt: contact.created_at,
    updatedAt: contact.updated_at
  };
}

function fieldOptions(fieldName: string, fallback: ContactFieldOption[]): ContactFieldOption[] {
  return fields.value?.fields.find((field) => field.field_name === fieldName)?.options ?? fallback;
}

function fieldLabel(fieldName: string, fallback: string): string {
  return fields.value?.fields.find((field) => field.field_name === fieldName)?.label ?? fallback;
}

function contactNameLabel(): string {
  const firstName = fieldLabel("first_name", "First Name");
  const lastName = fieldLabel("last_name", "Last Name");
  return firstName === "First Name" && lastName === "Last Name" ? "Name" : `${firstName} / ${lastName}`;
}

async function handleApiFailure(
    error: unknown,
    fallback: string,
    target: "page" | "details" = "page"
) {
  if (getApiErrorStatus(error) === 401) {
    sessionStore.clearSession();
    await router.push("/login");
    return;
  }

  const message = getApiErrorMessage(error, fallback);

  if (target === "details") {
    detailsError.value = message;
  } else {
    pageError.value = message;
  }
}

function readStoredDetailsWidth(): number {
  const value = Number(window.localStorage.getItem(DETAILS_WIDTH_STORAGE_KEY));
  return Number.isFinite(value) ? clamp(value, DETAILS_MIN_WIDTH, DETAILS_MAX_WIDTH) : 520;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-neutral-100 text-neutral-900">
    <ConsoleSidebar/>

    <main class="flex min-w-0 flex-1 flex-col gap-3 p-4">
      <header class="flex min-h-10 items-center gap-3 px-1">
        <h1 class="text-base font-semibold text-neutral-800">Contacts</h1>
        <p v-if="pageError" class="ml-4 rounded-md bg-red-50 px-3 py-1 text-sm text-red-700">{{ pageError }}</p>
      </header>

      <div class="flex min-h-0 flex-1 gap-3">
        <ContactsTable
            :rows="rows"
            :selected-key="selectedKey"
            :is-loading="isLoading"
            :count="tableCount"
            :labels="tableLabels"
            @select="selectRow"
            @create="createDraftRow"
        />

        <template v-if="selectedRow">
          <div
              class="w-1 cursor-col-resize rounded-full bg-transparent transition-colors hover:bg-neutral-300"
              :class="isResizing ? 'bg-neutral-300' : ''"
              title="Resize details"
              @mousedown="startResize"
          />
          <div class="min-h-0 shrink-0" :style="{width: `${detailsWidth}px`}">
            <ContactDetailsPanel
                :row="selectedRow"
                :status-options="statusOptions"
                :tag-options="tagOptions"
                :is-saving="isSaving"
                :is-deleting="isDeleting"
                :error="detailsError"
                @close="closeDetails"
                @save="saveContact"
                @delete="deleteSelectedContact"
            />
          </div>
        </template>
      </div>
    </main>
  </div>
</template>
