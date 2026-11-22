import {
  ref,
  shallowRef,
  watch,
  onScopeDispose,
  type Ref,
  type ShallowRef,
} from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { feedKeys } from "./feed.query-keys";
import { useFeedScope } from "./use-feed-scope";
import { FeedApiError } from "./feed.types";
import { FeedRequestGuard } from "./feed.request-guard";
export interface FeedAction<I, O> {
  pending: Ref<boolean>;
  error: ShallowRef<unknown>;
  execute(input: I): Promise<{ value: O } | undefined>;
}
export function useFeedAction<I, O>(
  action: (input: I, signal: AbortSignal) => Promise<O>,
): FeedAction<I, O> {
  const scope = useFeedScope(),
    client = useQueryClient(),
    pending = ref(false),
    error = shallowRef<unknown>();
  const guard = new FeedRequestGuard();
  const stamp = (): string => JSON.stringify(scope.value);
  watch(
    stamp,
    () => {
      guard.cancel();
      pending.value = false;
      error.value = undefined;
    },
    { flush: "sync" },
  );
  onScopeDispose(() => {
    guard.dispose();
  });
  async function execute(input: I): Promise<{ value: O } | undefined> {
    if (pending.value || !scope.value[0] || !scope.value[1]) return;
    const request = guard.start();
    if (!request) return;
    pending.value = true;
    error.value = undefined;
    const current = (): boolean => guard.current(request);
    try {
      const value = await action(input, request.signal);
      if (!current()) return;
      // Do not refetch into a live editor until it acknowledges the sent draft.
      await client.invalidateQueries({
        queryKey: feedKeys.root(scope.value),
        refetchType: "none",
      });
      if (current()) return { value };
    } catch (reason: unknown) {
      if (current()) {
        error.value = reason;
        if (reason instanceof FeedApiError && reason.status === 409)
          await client.invalidateQueries({
            queryKey: feedKeys.root(scope.value),
          });
      }
    } finally {
      if (current()) {
        pending.value = false;
        guard.finish(request);
      }
    }
    return undefined;
  }
  return { pending, error, execute };
}
