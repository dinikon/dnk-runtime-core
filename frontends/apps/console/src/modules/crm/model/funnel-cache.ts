import type { QueryClient } from "@tanstack/vue-query";

export async function invalidateCrmFunnelCache(
  client: QueryClient,
  scope: readonly unknown[],
): Promise<void> {
  await client.invalidateQueries({
    predicate: (query) =>
      [
        "sales-detail",
        "sales-list",
        "sales-column",
        "sales-conversion",
      ].includes(String(query.queryKey[0])) &&
      query.queryKey[1] === scope[0] &&
      query.queryKey[2] === scope[1],
  });
}
