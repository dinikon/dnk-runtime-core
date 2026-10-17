<script setup lang="ts">
import { computed, ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { useCompaniesQuery } from "../model/use-companies-query";
import {
  useCreateCompany,
  useDeleteCompany,
} from "../model/use-company-mutations";
import { crmRecordRoute } from "../model/use-crm-navigation";
import { crmKeys } from "../model/crm.query-keys";
import type { Company, CompanyInput } from "../model/crm.types";
import CrmCollectionBody from "../ui/common/CrmCollectionBody.vue";
import CrmPageHeader from "../ui/common/CrmPageHeader.vue";
import DeleteCrmEntityDialog from "../ui/common/DeleteCrmEntityDialog.vue";
import CompaniesTable from "../ui/companies/CompaniesTable.vue";
import CreateCompanyDialog from "../ui/companies/CreateCompanyDialog.vue";

const router = useRouter();
const queryClient = useQueryClient();
const companies = useCompaniesQuery();
const createMutation = useCreateCompany();
const deleteMutation = useDeleteCompany();
const createOpen = ref(false);
const deleting = ref<Company | null>(null);
const items = computed(() => companies.data.value ?? []);

async function create(input: CompanyInput) {
  try {
    const company = await createMutation.mutateAsync(input);
    createOpen.value = false;
    await router.push(crmRecordRoute("companies", company.id));
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
    queryClient.removeQueries({ queryKey: crmKeys.detail("companies", id) });
    queryClient.removeQueries({ queryKey: crmKeys.relations("companies", id) });
    queryClient.removeQueries({ queryKey: crmKeys.points("companies", id) });
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
      title="Компании"
      description="Компании и организации вашего рабочего пространства."
      action-label="Новая компания"
      @create="createOpen = true"
    />
    <CrmCollectionBody
      :pending="companies.isPending.value"
      :error="companies.isError.value"
      :empty="items.length === 0"
      empty-title="Компаний пока нет"
      empty-description="Создайте первую компанию в CRM."
      @retry="companies.refetch()"
    >
      <template #empty-action
        ><Button @click="createOpen = true">Создать компанию</Button></template
      >
      <CompaniesTable :items="items" @delete="deleting = $event" />
    </CrmCollectionBody>
    <CreateCompanyDialog
      v-model:open="createOpen"
      :pending="createMutation.isPending.value"
      @submit="create"
    />
    <DeleteCrmEntityDialog
      :open="deleting !== null"
      label="компанию"
      :entity-name="deleting?.legalName ?? ''"
      :pending="deleteMutation.isPending.value"
      @update:open="!$event && (deleting = null)"
      @confirm="confirmDelete"
    />
  </div>
</template>
