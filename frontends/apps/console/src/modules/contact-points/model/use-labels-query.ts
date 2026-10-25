import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { contactPointsApi } from "../api/contact-points.api";
export const contactPointKeys = {
  labels: ["contact-points", "labels"] as const,
};
export function useContactPointLabels(
  enabled: MaybeRefOrGetter<boolean> = true,
) {
  const tenant = useTenantStore(),
    user = useUserStore();
  const scope = computed(() => [
    tenant.tenant?.tenant_id ?? null,
    user.user?.id ?? null,
  ]);
  useScopedQueryCache(scope, "contact-points", 2);
  return useQuery({
    queryKey: computed(() => [
      ...contactPointKeys.labels,
      tenant.tenant?.tenant_id ?? null,
      user.user?.id ?? null,
    ]),
    queryFn: ({ signal }) => contactPointsApi.labels(signal),
    enabled: computed(() => toValue(enabled)),
  });
}
