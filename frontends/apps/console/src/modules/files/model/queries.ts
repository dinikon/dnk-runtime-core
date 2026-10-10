import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useTenantStore } from "@/app/stores/tenant";
import { filesApi } from "../api/files.api";
export function useFileStorage() {
  const store = useTenantStore();
  const tenant = computed(() => store.tenant?.tenant_id ?? "");
  const enabled = computed(() => !!tenant.value);
  const providers = useQuery({
    queryKey: computed(() => ["files", tenant.value, "providers"]),
    queryFn: ({ signal }) => filesApi.providers(signal),
    enabled,
    retry: false,
  });
  const buckets = useQuery({
    queryKey: computed(() => ["files", tenant.value, "buckets"]),
    queryFn: ({ signal }) => filesApi.buckets(signal),
    enabled,
    retry: false,
  });
  return { providers, buckets };
}
