import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { computed, toValue, type MaybeRefOrGetter } from "vue";
import type { CloudStatus } from "./cloud.types";
import { cloudApi } from "../api/cloud.api";
import { authQueryKeys } from "./auth.query-keys";

export function useCloudStatusQuery(
  tenantId: MaybeRefOrGetter<string | null>,
): UseQueryReturnType<CloudStatus, Error> {
  return useQuery({
    queryKey: computed(() => authQueryKeys.cloudStatus(toValue(tenantId))),
    queryFn: ({ signal }) => cloudApi.status(signal),
    enabled: false,
    retry: false,
  });
}
