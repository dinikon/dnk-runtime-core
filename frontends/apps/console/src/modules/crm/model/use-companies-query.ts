import { useQuery } from "@tanstack/vue-query";
import { crmCompaniesApi } from "../api/crm.api";
import { CRM_QUERY_STALE_TIME, crmKeys } from "./crm.query-keys";

export function useCompaniesQuery() {
  return useQuery({
    queryKey: crmKeys.list("companies"),
    queryFn: ({ signal }) => crmCompaniesApi.list(signal),
    staleTime: CRM_QUERY_STALE_TIME,
  });
}
