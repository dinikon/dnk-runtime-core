<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { crmCompaniesApi, crmContactsApi } from "../api/crm.api";
import { CRM_QUERY_STALE_TIME, crmKeys } from "../model/crm.query-keys";
import { useDeleteContact } from "../model/use-contact-mutations";
import { useDeleteCompany } from "../model/use-company-mutations";
import type { CrmKind } from "../model/crm.types";
import CrmRecordOverview from "../ui/common/CrmRecordOverview.vue";
import CrmCoreEditor from "../ui/common/CrmCoreEditor.vue";
import CrmRelationsEditor from "../ui/common/CrmRelationsEditor.vue";
import CrmContactPointsEditor from "../ui/common/CrmContactPointsEditor.vue";
import DeleteCrmEntityDialog from "../ui/common/DeleteCrmEntityDialog.vue";

const props = defineProps<{ kind: CrmKind; id: string }>();
const router = useRouter();
const queryClient = useQueryClient();
const detail = useQuery({
  queryKey: computed(() => crmKeys.detail(props.kind, props.id)),
  queryFn: async ({ signal }) =>
    props.kind === "contacts"
      ? await crmContactsApi.get(props.id, signal)
      : await crmCompaniesApi.get(props.id, signal),
  staleTime: CRM_QUERY_STALE_TIME,
});
const contactDelete = useDeleteContact();
const companyDelete = useDeleteCompany();
const deleteOpen = ref(false);
const pending = computed(
  () => contactDelete.isPending.value || companyDelete.isPending.value,
);
const title = computed(() => {
  const item = detail.data.value;
  return item
    ? "displayName" in item
      ? item.displayName
      : item.legalName
    : "Запись CRM";
});
async function remove() {
  try {
    if (props.kind === "contacts") await contactDelete.mutateAsync(props.id);
    else await companyDelete.mutateAsync(props.id);
    deleteOpen.value = false;
    await router.push({
      name: props.kind === "contacts" ? "crm-contacts" : "crm-companies",
    });
    queryClient.removeQueries({
      queryKey: crmKeys.detail(props.kind, props.id),
    });
    queryClient.removeQueries({
      queryKey: crmKeys.relations(props.kind, props.id),
    });
    queryClient.removeQueries({
      queryKey: crmKeys.points(props.kind, props.id),
    });
  } catch {
    /* mutation displays the API error */
  }
}
</script>

<template>
  <div
    class="flex min-h-0 min-w-0 flex-col gap-5 overflow-x-hidden overflow-y-auto pb-6"
  >
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex flex-col gap-1">
        <RouterLink
          :to="{ name: kind === 'contacts' ? 'crm-contacts' : 'crm-companies' }"
          class="text-sm text-muted-foreground hover:underline"
        >
          ← {{ kind === "contacts" ? "Контакты" : "Компании" }}
        </RouterLink>
        <h1 class="text-2xl font-semibold tracking-tight">{{ title }}</h1>
      </div>
      <Button
        variant="destructive"
        :disabled="!detail.data.value"
        @click="deleteOpen = true"
        >Удалить</Button
      >
    </header>
    <CrmRecordOverview :kind="kind" :id="id" :show-extensions="false" />
    <template v-if="detail.data.value">
      <CrmCoreEditor :kind="kind" :id="id" />
      <CrmRelationsEditor :kind="kind" :id="id" />
      <CrmContactPointsEditor :kind="kind" :id="id" />
    </template>
    <DeleteCrmEntityDialog
      :open="deleteOpen"
      :label="kind === 'contacts' ? 'контакт' : 'компанию'"
      :entity-name="title"
      :pending="pending"
      @update:open="deleteOpen = $event"
      @confirm="remove"
    />
  </div>
</template>
