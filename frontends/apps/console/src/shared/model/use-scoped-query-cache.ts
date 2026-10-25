import { watch, type Ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
/** Remove the former identity's data without touching queries for the new scope. */
export function useScopedQueryCache(
  scope: Ref<readonly (string | null)[]>,
  namespace: string,
  offset = 1,
): void {
  const client = useQueryClient();
  watch(
    scope,
    (current, previous) => {
      if (
        !previous ||
        current.every((value, index) => value === previous[index])
      )
        return;
      const matches = (key: readonly unknown[] | undefined): boolean =>
        !!key &&
        typeof key[0] === "string" &&
        key[0].startsWith(namespace) &&
        previous.every((value, index) => key[offset + index] === value);
      void client.cancelQueries({
        predicate: (query) => matches(query.queryKey),
      });
      client.removeQueries({ predicate: (query) => matches(query.queryKey) });
      for (const mutation of client.getMutationCache().getAll())
        if (matches(mutation.options.mutationKey))
          client.getMutationCache().remove(mutation);
    },
    { flush: "sync" },
  );
}
