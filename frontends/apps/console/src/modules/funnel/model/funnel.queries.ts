import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import { funnelKeys } from "./funnel.query-keys";
import type { Funnel, FunnelDetails, FunnelPage } from "./funnel.types";
import type { UseQueryReturnType } from "@tanstack/vue-query";
import { computed, type Ref, type ComputedRef } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { funnelApi } from "../api/funnel.api";
export function useFunnelScope(): ComputedRef<(string | null)[]> {
  const t = useTenantStore(),
    u = useUserStore();
  const scope = computed(() => [
    t.tenant?.tenant_id ?? null,
    u.user?.id ?? null,
  ]);
  useScopedQueryCache(scope, "funnel");
  return scope;
}
export function useFunnels(
  modelKey: Ref<string>,
  search: Ref<string> = computed(() => ""),
  offset: Ref<number> = computed(() => 0),
): UseQueryReturnType<FunnelPage, Error> {
  const scope = useFunnelScope();
  return useQuery({
    queryKey: computed(() =>
      funnelKeys.list(scope.value, modelKey.value, search.value, offset.value),
    ),
    queryFn: ({ signal }) =>
      funnelApi.list(modelKey.value, search.value, offset.value, signal),
  });
}
export function useFunnel(
  id: Ref<string>,
): UseQueryReturnType<FunnelDetails, Error> {
  const scope = useFunnelScope();
  return useQuery({
    queryKey: computed(() => funnelKeys.detail(scope.value, id.value)),
    queryFn: ({ signal }) => funnelApi.get(id.value, signal),
    enabled: computed(() => !!id.value),
  });
}

export function useFunnelOptions(
  modelKey: Ref<string>,
): UseQueryReturnType<{ items: Funnel[] }, Error> {
  const scope = useFunnelScope();
  return useQuery({
    queryKey: computed(() => funnelKeys.options(scope.value, modelKey.value)),
    queryFn: async ({ signal }) => ({
      items: await funnelApi.options(modelKey.value, signal),
    }),
  });
}
