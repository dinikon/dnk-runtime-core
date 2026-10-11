import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { filesApi } from "../api/files.api";
import { filesKeys } from "./query-keys";
import type { FilesFilters } from "./types";
export function useFilesQuery(
  filters: Ref<FilesFilters>,
  active: Ref<boolean>,
) {
  const store = useTenantStore();
  const tenant = computed(() => store.tenant?.tenant_id ?? "");
  return useQuery({
    queryKey: computed(() => filesKeys.files(tenant.value, filters.value)),
    queryFn: ({ signal }) => filesApi.list(filters.value, signal),
    enabled: computed(() => !!tenant.value && active.value),
    retry: false,
  });
}
