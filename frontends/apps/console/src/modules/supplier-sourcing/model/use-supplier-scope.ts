import { computed, type ComputedRef } from "vue";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import type { SupplierScope } from "./supplier-source.types";

export interface SupplierScopeState {
  key: ComputedRef<SupplierScope>;
  ready: ComputedRef<boolean>;
  error: ComputedRef<string>;
}

export function useSupplierScope(): SupplierScopeState {
  const tenant = useTenantStore(),
    user = useUserStore();
  const key = computed<SupplierScope>(() => [
    tenant.tenant?.tenant_id ?? null,
    user.user?.id ?? null,
    String(user.sessionRevision),
  ]);
  useScopedQueryCache(key, "supplier-sourcing");
  return {
    key,
    ready: computed(
      () =>
        !!key.value[0] &&
        !!key.value[1] &&
        tenant.isTenantAvailable &&
        user.sessionStatus === "ready",
    ),
    error: computed(() =>
      tenant.tenant && !tenant.isResolvingTenant && !tenant.isTenantAvailable
        ? "Рабочее пространство недоступно."
        : "",
    ),
  };
}
