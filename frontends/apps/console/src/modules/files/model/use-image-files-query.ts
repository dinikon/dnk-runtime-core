import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import { filesApi } from "../api/files.api";
import type { FilesPageResult, FilesFilters } from "./types";
import { filesKeys, type FilePickerScope } from "./query-keys";

export function useImageFilesQuery(
  filters: Ref<FilesFilters>,
  active: Ref<boolean>,
): UseQueryReturnType<FilesPageResult, Error> {
  const tenant = useTenantStore(),
    user = useUserStore();
  const scope = computed<FilePickerScope>(() => [
    tenant.tenant?.tenant_id ?? null,
    user.user?.id ?? null,
    String(user.sessionRevision),
  ]);
  useScopedQueryCache(scope, "files");
  return useQuery({
    queryKey: computed(() => filesKeys.images(scope.value, filters.value)),
    queryFn: ({ signal }) =>
      filesApi.list({ ...filters.value, category: "images" }, signal),
    enabled: computed(
      () => !!scope.value[0] && !!scope.value[1] && active.value,
    ),
    retry: false,
  });
}
