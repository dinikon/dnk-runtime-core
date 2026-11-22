import { computed, type ComputedRef } from "vue";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import type { FeedScope } from "./feed.query-keys";
export function useFeedScope(): ComputedRef<FeedScope> {
  const tenant = useTenantStore(),
    user = useUserStore();
  const scope = computed<FeedScope>(() => [
    tenant.tenant?.tenant_id ?? null,
    user.user?.id ?? null,
    String(user.sessionRevision),
  ]);
  useScopedQueryCache(scope, "feed-builder");
  return scope;
}
