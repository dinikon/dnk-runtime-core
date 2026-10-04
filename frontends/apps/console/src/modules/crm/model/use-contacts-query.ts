import { useQuery } from "@tanstack/vue-query";
import { crmContactsApi } from "../api/crm.api";
import { CRM_QUERY_STALE_TIME, crmKeys } from "./crm.query-keys";

export function useContactsQuery() {
  return useQuery({
    queryKey: crmKeys.list("contacts"),
    queryFn: ({ signal }) => crmContactsApi.list(signal),
    staleTime: CRM_QUERY_STALE_TIME,
  });
}
