import { computed } from "vue";
import { useFunnelScope } from "./funnel.queries";
import type { UseMutationReturnType } from "@tanstack/vue-query";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { funnelApi } from "../api/funnel.api";
import type { FunnelDraft } from "./funnel.types";
export function useSaveFunnel(): UseMutationReturnType<
  { id: string },
  Error,
  { id?: string; draft: FunnelDraft; revision?: number },
  unknown
> {
  const client = useQueryClient(),
    scope = useFunnelScope();
  return useMutation({
    mutationKey: computed(() => ["funnel-save", ...scope.value]),
    mutationFn: (v: { id?: string; draft: FunnelDraft; revision?: number }) =>
      v.id
        ? funnelApi.update(v.id, v.draft, v.revision!)
        : funnelApi.create(v.draft),
    onSuccess: async () => {
      await client.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "funnel" ||
          q.queryKey[0] === "funnels" ||
          q.queryKey[0] === "funnel-options",
      });
    },
  });
}
