<script setup lang="ts">
import { getApiErrorStatus } from "@/app/providers/http";
import { useCrmCard } from "../model/use-crm-card";
import { crmCompaniesApi } from "../api/crm.api";
import DiscardCrmChangesDialog from "../ui/common/DiscardCrmChangesDialog.vue";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import {
  useContactPointLabels,
  contactPointServerErrors,
} from "@/modules/contact-points";
import type { ContactPointErrors } from "@/modules/contact-points";
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { useCrmListState } from "../model/use-crm-list-state";
import { useCompaniesQuery } from "../model/use-companies-query";
import {
  useCreateCompany,
  useDeleteCompany,
  useUpdateCompany,
} from "../model/use-company-mutations";
import type { Company, CompanyInput } from "../model/crm.types";
import CrmCollectionBody from "../ui/common/CrmCollectionBody.vue";
import CrmPageHeader from "../ui/common/CrmPageHeader.vue";
import CrmPagination from "../ui/common/CrmPagination.vue";
import CrmSearchBar from "../ui/common/CrmSearchBar.vue";
import DeleteCrmEntityDialog from "../ui/common/DeleteCrmEntityDialog.vue";
import CompaniesTable from "../ui/companies/CompaniesTable.vue";
import CompanyFormDialog from "../ui/companies/CompanyFormDialog.vue";

const { page, pageSize, params, search, setPage } = useCrmListState();
const companies = useCompaniesQuery(params);
const createMutation = useCreateCompany();
const updateMutation = useUpdateCompany();
const deleteMutation = useDeleteCompany();
const pointErrors = ref<ContactPointErrors>({});
const deleting = ref<Company | null>(null);
const items = computed(() => companies.data.value?.items ?? []);
const total = computed(() => companies.data.value?.total ?? 0);
const formPending = computed(
  () => createMutation.isPending.value || updateMutation.isPending.value,
);

const {
  editing,
  formOpen,
  dirty,
  loading,
  loadError,
  conflict,
  discardOpen,
  decideDiscard,
  openCreate,
  openEdit,
  close,
  saved,
  reload,
  navigate,
} = useCrmCard("companies", crmCompaniesApi.get, formPending);
const labels = useContactPointLabels(formOpen);
watch(formOpen, (open) => {
  if (open) pointErrors.value = {};
});

async function submitForm(input: CompanyInput) {
  pointErrors.value = {};
  try {
    if (editing.value) {
      await updateMutation.mutateAsync({ id: editing.value.id, input });
    } else {
      await createMutation.mutateAsync(input);
    }
  } catch (cause) {
    pointErrors.value = contactPointServerErrors(cause, input);
    conflict.value = getApiErrorStatus(cause) === 409;
    return;
  }
  await saved();
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
      title="Компании"
      description="Компании и организации вашего рабочего пространства."
      action-label="Новая компания"
      @create="openCreate"
    />
    <CrmSearchBar v-model="search" placeholder="Поиск по названию" />
    <CrmCollectionBody
      :pending="companies.isPending.value"
      :error="companies.isError.value"
      :empty="items.length === 0"
      :search-active="params.q.length > 0"
      empty-title="Компаний пока нет"
      empty-description="Создайте первую компанию в CRM."
      @retry="companies.refetch()"
    >
      <template #empty-action>
        <Button @click="openCreate">Создать компанию</Button>
      </template>
      <CompaniesTable
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
    <Alert v-if="loading || loadError" role="status">
      <AlertDescription
        ><Spinner v-if="loading" />{{
          loading ? "Загрузка карточки…" : loadError
        }}
        <Button v-if="loadError" variant="outline" @click="reload"
          >Повторить</Button
        >
        <Button v-if="loadError" variant="ghost" @click="close">Закрыть</Button>
      </AlertDescription>
    </Alert>

    <CompanyFormDialog
      :open="formOpen"
      :company="editing"
      :pending="formPending"
      :labels="labels.data.value ?? []"
      :labels-loading="labels.isFetching.value"
      :labels-error="labels.isError.value"
      :point-errors="pointErrors"
      :conflict="conflict"
      @reload="reload"
      @navigate="navigate"
      @dirty-change="dirty = $event"
      @retry-labels="labels.refetch()"
      @clear-point-errors="
        (keys) => keys.forEach((key) => delete pointErrors[key])
      "
      @update:open="!$event && close()"
      @submit="submitForm"
    />
    <DiscardCrmChangesDialog :open="discardOpen" @decide="decideDiscard" />
    <DeleteCrmEntityDialog
      :open="deleting !== null"
      label="компанию"
      :entity-name="deleting?.name ?? ''"
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
