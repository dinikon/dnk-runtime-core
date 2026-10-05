import { computed, type Ref } from "vue";
import { useInfiniteQuery, useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { inventoryApi } from "../api/inventory.api";
export function useInventoryTenant() {
  const store = useTenantStore();
  return computed(() => store.tenant?.tenant_id ?? "unresolved");
}
export const skuKeys = {
  list: (tenant: string) => ["inventory", tenant, "skus", "list"] as const,
  detail: (tenant: string, id: string) =>
    ["inventory", tenant, "skus", "detail", id] as const,
};
export function useSkus() {
  const tenant = useInventoryTenant();
  return useInfiniteQuery({
    queryKey: computed(() => skuKeys.list(tenant.value)),
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      inventoryApi.listSkus(pageParam, signal),
    getNextPageParam: (last, _pages, offset) =>
      last.length === 50 ? offset + 50 : undefined,
    retry: false,
  });
}
export function useSku(id: Ref<string>) {
  const tenant = useInventoryTenant();
  return useQuery({
    queryKey: computed(() => skuKeys.detail(tenant.value, id.value)),
    queryFn: ({ signal }) => inventoryApi.getSku(id.value, signal),
    enabled: computed(() => !!id.value),
    retry: false,
  });
}
