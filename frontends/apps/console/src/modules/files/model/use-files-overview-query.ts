import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { filesApi } from "../api/files.api";
import { filesKeys } from "./query-keys";
export function useFilesOverviewQuery(buckets: Ref<string[]>) {
  const store = useTenantStore();
  const tenant = computed(() => store.tenant?.tenant_id ?? "");
  return useQuery({
    queryKey: computed(() => filesKeys.overview(tenant.value, buckets.value)),
    queryFn: ({ signal }) => filesApi.overview(buckets.value, signal),
    enabled: computed(() => !!tenant.value),
    retry: false,
  });
}
