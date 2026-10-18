import { computed, onBeforeUnmount } from "vue";
import { type UseMutationReturnType, useMutation } from "@tanstack/vue-query";
import { channelsApi } from "../../api/channels.api";
import { ChannelsApiError } from "../../api/channels.error";
import type { UpdateConnectionInput, ConnectionSaved } from "../channels.types";
import type { ChannelsContext } from "../use-channels-context";
type UpdateConnectionVariables = Omit<UpdateConnectionInput, "credentials">;
type UpdateConnectionMutation = Pick<
  UseMutationReturnType<
    ConnectionSaved,
    ChannelsApiError,
    UpdateConnectionVariables,
    string
  >,
  "isPending" | "reset"
> & { execute: (input: UpdateConnectionInput) => Promise<ConnectionSaved> };
export function useUpdateConnection(
  ctx: ChannelsContext,
): UpdateConnectionMutation {
  // Secrets live only in this in-flight closure, never in TanStack mutation variables.
  let credentials: Record<string, string> | undefined;
  let executing = false;
  const mutation = useMutation<
    ConnectionSaved,
    ChannelsApiError,
    UpdateConnectionVariables,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) =>
      channelsApi.updateConnection(
        { ...input, ...(credentials ? { credentials } : {}) },
        ctx.signal(),
      ),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _variables, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
  onBeforeUnmount(() => {
    credentials = undefined;
  });
  async function execute(
    input: UpdateConnectionInput,
  ): Promise<ConnectionSaved> {
    if (executing) throw new ChannelsApiError(409, "operation_in_progress");
    executing = true;
    const { credentials: secretValues, ...variables } = input;
    credentials = secretValues ? { ...secretValues } : undefined;
    try {
      return await mutation.mutateAsync(variables);
    } finally {
      credentials = undefined;
      executing = false;
      mutation.reset();
    }
  }
  return {
    isPending: computed(() => mutation.isPending.value),
    reset: mutation.reset,
    execute,
  };
}
