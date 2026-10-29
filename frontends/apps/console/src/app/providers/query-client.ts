import { MutationCache, QueryClient } from "@tanstack/vue-query";
import { publicationCatalogMutationKey } from "@/modules/channels";
import { invalidateCatalogItems } from "@/modules/catalog";
import { funnelSaveMutationKey } from "@/modules/funnel";
import { invalidateCrmFunnelCache } from "@/modules/crm";

export function createQueryClient(): QueryClient {
  const client = new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: async (_data, _variables, _context, mutation) => {
        const key = mutation.options.mutationKey;
        if (
          key?.[0] === publicationCatalogMutationKey &&
          Array.isArray(_context) &&
          typeof _context[0] === "string"
        )
          await invalidateCatalogItems(client, _context[0]);
        if (key?.[0] === funnelSaveMutationKey)
          await invalidateCrmFunnelCache(client, key.slice(1));
      },
    }),
  });
  return client;
}
