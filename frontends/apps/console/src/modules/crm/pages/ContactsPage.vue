<script setup lang="ts">
import { computed, ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { useContactsQuery } from "../model/use-contacts-query";
import {
  useCreateContact,
  useDeleteContact,
} from "../model/use-contact-mutations";
import { crmRecordRoute } from "../model/use-crm-navigation";
import { crmKeys } from "../model/crm.query-keys";
import type { Contact, ContactInput } from "../model/crm.types";
import CrmCollectionBody from "../ui/common/CrmCollectionBody.vue";
import CrmPageHeader from "../ui/common/CrmPageHeader.vue";
import DeleteCrmEntityDialog from "../ui/common/DeleteCrmEntityDialog.vue";
import ContactsTable from "../ui/contacts/ContactsTable.vue";
import CreateContactDialog from "../ui/contacts/CreateContactDialog.vue";

const router = useRouter();
const queryClient = useQueryClient();
const contacts = useContactsQuery();
const createMutation = useCreateContact();
const deleteMutation = useDeleteContact();
const createOpen = ref(false);
const deleting = ref<Contact | null>(null);
const items = computed(() => contacts.data.value ?? []);

async function create(input: ContactInput) {
  try {
    const contact = await createMutation.mutateAsync(input);
    createOpen.value = false;
    await router.push(crmRecordRoute("contacts", contact.id));
  } catch {
    /* mutation displays the API error */
  }
}
async function confirmDelete() {
  if (!deleting.value) return;
  try {
    const id = deleting.value.id;
    await deleteMutation.mutateAsync(id);
    deleting.value = null;
    queryClient.removeQueries({ queryKey: crmKeys.detail("contacts", id) });
    queryClient.removeQueries({ queryKey: crmKeys.relations("contacts", id) });
    queryClient.removeQueries({ queryKey: crmKeys.points("contacts", id) });
  } catch {
    /* mutation displays the API error */
  }
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
      @create="createOpen = true"
    />
    <CrmCollectionBody
      :pending="contacts.isPending.value"
      :error="contacts.isError.value"
      :empty="items.length === 0"
      empty-title="Контактов пока нет"
      empty-description="Создайте первого клиента в CRM."
      @retry="contacts.refetch()"
    >
      <template #empty-action
        ><Button @click="createOpen = true">Создать контакт</Button></template
      >
      <ContactsTable :items="items" @delete="deleting = $event" />
    </CrmCollectionBody>
    <CreateContactDialog
      v-model:open="createOpen"
      :pending="createMutation.isPending.value"
      @submit="create"
    />
    <DeleteCrmEntityDialog
      :open="deleting !== null"
      label="контакт"
      :entity-name="deleting?.displayName ?? ''"
      :pending="deleteMutation.isPending.value"
      @update:open="!$event && (deleting = null)"
      @confirm="confirmDelete"
    />
  </div>
</template>
