import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useDocumentVisibility } from "@vueuse/core";
import { useTenantStore } from "@/app/stores/tenant";
import { filesApi } from "../api/files.api";
import { filesKeys } from "./query-keys";
import type { FilesFilters } from "./types";
export function useTrashQuery(
  filters: Ref<FilesFilters>,
  active: Ref<boolean>,
) {
  const store = useTenantStore();
  const tenant = computed(() => store.tenant?.tenant_id ?? "");
  const visibility = useDocumentVisibility();
  return useQuery({
    queryKey: computed(() => filesKeys.trash(tenant.value, filters.value)),
    queryFn: ({ signal }) => filesApi.trashList(filters.value, signal),
    enabled: computed(() => !!tenant.value && active.value),
    retry: false,
    refetchInterval: (query) =>
      active.value &&
      visibility.value === "visible" &&
      query.state.data?.items.some((item) => item.status === "purging")
        ? 5000
        : false,
  });
}
