import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { crmCompaniesApi } from "../api/crm.api";
import { companyKeys } from "./crm.query-keys";
import type { ListParams } from "./crm.types";

export function useCompaniesQuery(params: Ref<ListParams>) {
  return useQuery({
    queryKey: computed(() => companyKeys.list(params.value)),
    queryFn: ({ signal }) => crmCompaniesApi.list(params.value, signal),
  });
}
