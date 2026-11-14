import { MutationCache, QueryClient } from "@tanstack/vue-query";
import { inventoryItemUpdateTenant } from "@/modules/inventory";
import { invalidateCatalogItems } from "@/modules/catalog";
import { funnelSaveMutationKey } from "@/modules/funnel";
import { invalidateCrmFunnelCache } from "@/modules/crm";

export function createQueryClient(): QueryClient {
  const client = new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: async (_data, variables, _context, mutation) => {
        const key = mutation.options.mutationKey;
        const inventoryTenant = inventoryItemUpdateTenant(key, variables);
        if (inventoryTenant)
          await invalidateCatalogItems(client, inventoryTenant);
        if (key?.[0] === funnelSaveMutationKey)
          await invalidateCrmFunnelCache(client, key.slice(1));
      },
    }),
  });
  return client;
}
