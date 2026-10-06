import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { channelsApi } from "../api/channels.api";
export function useChannelTenant() {
  const store = useTenantStore();
  return computed(() => store.tenant?.tenant_id ?? "");
}
export function useChannels() {
  const tenant = useChannelTenant();
  return useQuery({
    queryKey: computed(() => ["channels", tenant.value, "list"]),
    queryFn: ({ signal }) => channelsApi.list(signal),
    enabled: computed(() => !!tenant.value),
    retry: false,
  });
}
export function useKinds() {
  const tenant = useChannelTenant();
  return useQuery({
    queryKey: computed(() => ["channels", tenant.value, "kinds"]),
    queryFn: ({ signal }) => channelsApi.kinds(signal),
    enabled: computed(() => !!tenant.value),
    retry: false,
  });
}
export function useChannel(id: Ref<string>) {
  const tenant = useChannelTenant();
  return useQuery({
    queryKey: computed(() => ["channels", tenant.value, "detail", id.value]),
    queryFn: ({ signal }) => channelsApi.get(id.value, signal),
    enabled: computed(() => !!tenant.value && !!id.value),
    retry: false,
    refetchOnWindowFocus: false,
  });
}
export function useChannelConfig(kind: Ref<string>) {
  const tenant = useChannelTenant();
  return useQuery({
    queryKey: computed(() => ["channels", tenant.value, "config", kind.value]),
    queryFn: ({ signal }) => channelsApi.config(kind.value, signal),
    enabled: computed(() => !!tenant.value && !!kind.value),
    retry: false,
    refetchOnWindowFocus: false,
  });
}
