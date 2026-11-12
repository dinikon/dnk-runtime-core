import { computed, type ComputedRef } from "vue";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import type { InventoryScope } from "./inventory-item.types";

export interface InventoryScopeState {
  key: ComputedRef<InventoryScope>;
  ready: ComputedRef<boolean>;
  error: ComputedRef<string>;
}

export function useInventoryScope(): InventoryScopeState {
  const tenant = useTenantStore(),
    user = useUserStore();
  const key = computed<InventoryScope>(() => [
    tenant.tenant?.tenant_id ?? null,
    user.user?.id ?? null,
    String(user.sessionRevision),
  ]);
  useScopedQueryCache(key, "inventory");
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
