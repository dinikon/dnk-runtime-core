<script setup lang="ts">
import { computed, ref } from "vue";
import { Button } from "@/components/ui/button";
import { useCrmListState } from "../model/use-crm-list-state";
import { useContactsQuery } from "../model/use-contacts-query";
import {
  useCreateContact,
  useDeleteContact,
  useUpdateContact,
} from "../model/use-contact-mutations";
import type { Contact, ContactInput } from "../model/crm.types";
import CrmCollectionBody from "../ui/common/CrmCollectionBody.vue";
import CrmPageHeader from "../ui/common/CrmPageHeader.vue";
import CrmPagination from "../ui/common/CrmPagination.vue";
import CrmSearchBar from "../ui/common/CrmSearchBar.vue";
import DeleteCrmEntityDialog from "../ui/common/DeleteCrmEntityDialog.vue";
import ContactFormDialog from "../ui/contacts/ContactFormDialog.vue";
import ContactsTable from "../ui/contacts/ContactsTable.vue";

const { page, pageSize, params, search, setPage } = useCrmListState();
const contacts = useContactsQuery(params);
const createMutation = useCreateContact();
const updateMutation = useUpdateContact();
const deleteMutation = useDeleteContact();
const formOpen = ref(false);
const editing = ref<Contact | null>(null);
const deleting = ref<Contact | null>(null);
const items = computed(() => contacts.data.value?.items ?? []);
const total = computed(() => contacts.data.value?.total ?? 0);
const formPending = computed(
  () => createMutation.isPending.value || updateMutation.isPending.value,
);

function openCreate() {
  editing.value = null;
  formOpen.value = true;
}

function openEdit(contact: Contact) {
  editing.value = contact;
  formOpen.value = true;
}

async function submitForm(input: ContactInput) {
  try {
    if (editing.value) {
      await updateMutation.mutateAsync({ id: editing.value.id, input });
    } else {
      await createMutation.mutateAsync(input);
    }
  } catch {
    return;
  }
  formOpen.value = false;
  editing.value = null;
}

async function confirmDelete() {
  if (!deleting.value) return;
  const shouldMoveBack = items.value.length === 1 && page.value > 1;
  try {
    await deleteMutation.mutateAsync(deleting.value.id);
  } catch {
    return;
  }
  deleting.value = null;
  if (shouldMoveBack) await setPage(page.value - 1);
}
</script>

<template>
  <div
    class="flex min-h-0 min-w-0 flex-col gap-5 overflow-x-hidden overflow-y-auto pb-6"
  >
    <CrmPageHeader
      eyebrow="CRM"
      title="Контакты"
      description="Клиенты — физические лица вашего рабочего пространства."
      action-label="Новый контакт"
      @create="openCreate"
    />
    <CrmSearchBar v-model="search" placeholder="Поиск по ФИО" />
    <CrmCollectionBody
      :pending="contacts.isPending.value"
      :error="contacts.isError.value"
      :empty="items.length === 0"
      :search-active="params.q.length > 0"
      empty-title="Контактов пока нет"
      empty-description="Создайте первого клиента в CRM."
      @retry="contacts.refetch()"
    >
      <template #empty-action>
        <Button @click="openCreate">Создать контакт</Button>
      </template>
      <ContactsTable
        :items="items"
        @edit="openEdit"
        @delete="deleting = $event"
      />
    </CrmCollectionBody>
    <CrmPagination
      :page="page"
      :total="total"
      :page-size="pageSize"
      @update:page="setPage"
    />
    <ContactFormDialog
      :open="formOpen"
      :contact="editing"
      :pending="formPending"
      @update:open="formOpen = $event"
      @submit="submitForm"
    />
    <DeleteCrmEntityDialog
      :open="deleting !== null"
      label="контакт"
      :entity-name="deleting?.displayName ?? ''"
      :pending="deleteMutation.isPending.value"
      @update:open="
        (open) => {
          if (!open) deleting = null;
        }
      "
      @confirm="confirmDelete"
    />
  </div>
</template>
