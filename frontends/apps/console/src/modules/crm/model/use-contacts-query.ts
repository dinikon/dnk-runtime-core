import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { crmContactsApi } from "../api/crm.api";
import { contactKeys } from "./crm.query-keys";
import type { ListParams } from "./crm.types";

export function useContactsQuery(params: Ref<ListParams>) {
  return useQuery({
    queryKey: computed(() => contactKeys.list(params.value)),
    queryFn: ({ signal }) => crmContactsApi.list(params.value, signal),
  });
}
