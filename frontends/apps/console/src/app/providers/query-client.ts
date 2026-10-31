import { MutationCache, QueryClient } from "@tanstack/vue-query";
import { funnelSaveMutationKey } from "@/modules/funnel";
import { invalidateCrmFunnelCache } from "@/modules/crm";

export function createQueryClient(): QueryClient {
  const client = new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: async (_data, _variables, _context, mutation) => {
        const key = mutation.options.mutationKey;
        if (key?.[0] === funnelSaveMutationKey)
          await invalidateCrmFunnelCache(client, key.slice(1));
      },
    }),
  });
  return client;
}
