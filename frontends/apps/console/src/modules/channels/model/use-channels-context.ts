import { type ComputedRef, computed, onBeforeUnmount, watch } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
import { channelsKeys } from "./channels.query-keys";
export interface ChannelsContext {
  scope: ComputedRef<string>;
  enabled: ComputedRef<boolean>;
  capture: () => () => boolean;
  refresh: (captured: string) => Promise<void>;
  signal: () => AbortSignal;
}
export function useChannelsContext(): ChannelsContext {
  const tenant = useTenantStore(),
    user = useUserStore(),
    cache = useQueryClient();
  const scope = computed(
    () => `${tenant.tenant?.tenant_id ?? ""}:${user.user?.id ?? ""}`,
  );
  const enabled = computed(
    () =>
      !!tenant.tenant?.tenant_id && !!user.user?.id && tenant.isTenantAvailable,
  );
  let mounted = true;
  let controller = new AbortController();
  onBeforeUnmount(() => {
    mounted = false;
    controller.abort();
  });
  function capture(): () => boolean {
    const captured = scope.value;
    return () => mounted && scope.value === captured && enabled.value;
  }
  async function refresh(captured: string): Promise<void> {
    if (scope.value === captured && enabled.value)
      await cache.invalidateQueries({ queryKey: channelsKeys.scope(captured) });
  }
  watch(
    scope,
    (_next, old) => {
      controller.abort();
      controller = new AbortController();
      void cache.cancelQueries({ queryKey: channelsKeys.scope(old) });
      cache.removeQueries({ queryKey: channelsKeys.scope(old) });
    },
    { flush: "sync" },
  );
  function signal(): AbortSignal {
    return controller.signal;
  }
  return { scope, enabled, capture, refresh, signal };
}
