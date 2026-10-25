import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import { computed, type ComputedRef } from "vue";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
export function useSalesScope(): ComputedRef<(string | null)[]> {
  const tenant = useTenantStore(),
    user = useUserStore();
  const scope = computed(() => [
    tenant.tenant?.tenant_id ?? null,
    user.user?.id ?? null,
  ]);
  useScopedQueryCache(scope, "sales-");
  return scope;
}
