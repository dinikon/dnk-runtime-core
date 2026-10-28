import { computed, type ComputedRef } from "vue";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import type { ChannelScope } from "./channel.query-keys";
export function useChannelScope(): ComputedRef<ChannelScope> {
  const tenant = useTenantStore(),
    user = useUserStore();
  const scope = computed<ChannelScope>(() => [
    tenant.tenant?.tenant_id ?? null,
    user.user?.id ?? null,
    String(user.sessionRevision),
  ]);
  useScopedQueryCache(
    computed(() => scope.value.map((v) => (v === null ? null : String(v)))),
    "channels",
  );
  return scope;
}
