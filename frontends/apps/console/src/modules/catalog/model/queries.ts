import { computed, type Ref } from "vue";
import { useInfiniteQuery, useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { catalogApi } from "../api/catalog.api";
import { isUuid } from "./forms";
export function useCatalogTenant() {
  const store = useTenantStore();
  return computed(() => store.tenant?.tenant_id ?? "unresolved");
}
export const productKey = (tenant: string, id: string) =>
  ["catalog", tenant, "product", id] as const;
export function useLocales() {
  const tenant = useCatalogTenant();
  return useQuery({
    queryKey: computed(() => ["catalog", tenant.value, "locales"]),
    queryFn: ({ signal }) => catalogApi.listLocales(signal),
    retry: false,
  });
}
export function useSkus() {
  const tenant = useCatalogTenant();
  return useInfiniteQuery({
    queryKey: computed(() => ["catalog", tenant.value, "skus"]),
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) => catalogApi.listSkus(pageParam, signal),
    getNextPageParam: (last, _pages, offset) =>
      last.length === 50 ? offset + 50 : undefined,
    retry: false,
  });
}
export function useProduct(id: Ref<string>, locale: Ref<string>) {
  const tenant = useCatalogTenant();
  return useQuery({
    queryKey: computed(() => [
      ...productKey(tenant.value, id.value),
      locale.value,
    ]),
    queryFn: ({ signal }) =>
      catalogApi.getProduct(id.value, locale.value, signal),
    enabled: computed(() => isUuid(id.value) && !!locale.value),
    retry: false,
  });
}
