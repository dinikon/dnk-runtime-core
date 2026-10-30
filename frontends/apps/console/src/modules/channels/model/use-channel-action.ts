import { ref, watch, onScopeDispose, type Ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useChannelScope } from "./use-channel-scope";
import { channelKeys } from "./channel.query-keys";
import { ChannelApiError } from "./channel.types";
import { channelErrorMessage } from "./channel.errors";
/** Secret-bearing arguments stay on the call stack, outside the mutation cache. */
export interface ChannelAction<I, O> {
  pending: Ref<boolean>;
  error: Ref<string>;
  execute(input: I): Promise<{ value: O } | undefined>;
}
export function useChannelAction<I, O>(
  action: (input: I, signal: AbortSignal) => Promise<O>,
  refetchType: "active" | "none" = "active",
): ChannelAction<I, O> {
  const scope = useChannelScope(),
    client = useQueryClient(),
    pending = ref(false),
    error = ref("");
  let alive = true,
    controller: AbortController | undefined;
  const stamp = (): string => JSON.stringify(scope.value);
  watch(
    stamp,
    () => {
      controller?.abort();
      pending.value = false;
      error.value = "";
    },
    { flush: "sync" },
  );
  onScopeDispose(() => {
    alive = false;
    controller?.abort();
  });
  async function execute(input: I): Promise<{ value: O } | undefined> {
    if (pending.value) return;
    const captured = stamp();
    controller = new AbortController();
    pending.value = true;
    error.value = "";
    try {
      const value = await action(input, controller.signal);
      if (!alive || stamp() !== captured) return;
      await client.invalidateQueries({
        queryKey: channelKeys.root(scope.value),
        refetchType,
      });
      if (!alive || stamp() !== captured) return;
      return { value };
    } catch (reason: unknown) {
      if (alive && stamp() === captured) {
        error.value = channelErrorMessage(reason);
        if (reason instanceof ChannelApiError && reason.status === 409)
          await client.invalidateQueries({
            queryKey: channelKeys.root(scope.value),
          });
      }
      return;
    } finally {
      if (alive && stamp() === captured) pending.value = false;
    }
  }
  return { pending, error, execute };
}
