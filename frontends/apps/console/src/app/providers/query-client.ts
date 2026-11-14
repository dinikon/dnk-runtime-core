import { MutationCache, QueryClient } from "@tanstack/vue-query";
import { inventoryItemUpdateTenant } from "@/modules/inventory";
import { funnelSaveMutationKey } from "@/modules/funnel";
import { invalidateCrmFunnelCache } from "@/modules/crm";

export function createQueryClient(): QueryClient {
  const client = new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: async (_data, variables, _context, mutation) => {
        const key = mutation.options.mutationKey;
        const inventoryTenant = inventoryItemUpdateTenant(key, variables);
        if (inventoryTenant) {
          // Публичный контракт Catalog загружается лениво вместе с его UI-зависимостями.
          // Сбой обновления представлений не меняет подтверждённый результат PATCH.
          try {
            const { invalidateCatalogItems } =
              await import("@/modules/catalog");
            if (inventoryItemUpdateTenant(key, variables) === inventoryTenant)
              await invalidateCatalogItems(client, inventoryTenant);
          } catch (error: unknown) {
            console.warn(
              "Не удалось обновить представления Catalog после сохранения SKU.",
              error,
            );
          }
        }
        if (key?.[0] === funnelSaveMutationKey)
          await invalidateCrmFunnelCache(client, key.slice(1));
      },
    }),
  });
  return client;
}
