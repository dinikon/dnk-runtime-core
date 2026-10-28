import { computed } from "vue";
import { funnelSaveMutationKey } from "./funnel.query-keys";
import { useFunnelScope } from "./funnel.queries";
import type { UseMutationReturnType } from "@tanstack/vue-query";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { funnelApi } from "../api/funnel.api";
import type { FunnelDraft, SaveFunnelResult } from "./funnel.types";
export function useSaveFunnel(): UseMutationReturnType<
  SaveFunnelResult,
  Error,
  { id?: string; draft: FunnelDraft; revision?: number },
  unknown
> {
  const client = useQueryClient(),
    scope = useFunnelScope();
  return useMutation({
    mutationKey: computed(() => [funnelSaveMutationKey, ...scope.value]),
    mutationFn: (v: { id?: string; draft: FunnelDraft; revision?: number }) =>
      v.id
        ? funnelApi.update(v.id, v.draft, v.revision!)
        : funnelApi.create(v.draft),
    onMutate: () => [...scope.value],
    onSuccess: async (_result, _variables, context) => {
      const submittedScope = context as (string | null)[];
      await client.invalidateQueries({
        predicate: (q) =>
          ["funnel", "funnels", "funnel-options"].includes(
            String(q.queryKey[0]),
          ) &&
          q.queryKey[1] === submittedScope[0] &&
          q.queryKey[2] === submittedScope[1],
      });
    },
  });
}
